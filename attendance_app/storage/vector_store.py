"""Persistent local FAISS vector index backed by SQLite enrollment records."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Protocol

import numpy as np

from config.settings import APP_ROOT, FACE_MATCH_THRESHOLD
from storage.database import FaceDatabase

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FaceMatch:
    employee_id: str
    name: str
    squared_l2_distance: float
    pose: str


class VectorStore(Protocol):
    def add_employee(
        self,
        employee_id: str,
        name: str,
        samples: list[tuple[str, np.ndarray]],
    ) -> None: ...

    def employee_exists(self, employee_id: str) -> bool: ...

    def remove_employee(self, employee_id: str) -> bool: ...

    def search(self, vector: np.ndarray) -> FaceMatch | None: ...

    def rebuild(self) -> int: ...


class FaissVectorStore:
    """Exact squared-L2 search with an incrementally maintained ID-mapped index."""

    DIMENSION = 512
    DEFAULT_THRESHOLD = FACE_MATCH_THRESHOLD

    def __init__(
        self,
        database: FaceDatabase | None = None,
        index_path: str | Path | None = None,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> None:
        import faiss

        self._faiss = faiss
        self.database = database or FaceDatabase()
        self.index_path = (
            Path(index_path)
            if index_path
            else APP_ROOT / "data" / "faces.faiss"
        )
        self.index_path = self.index_path.expanduser().resolve()
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.threshold = float(threshold)
        self.index = self._new_index()
        self._last_save_succeeded = False
        self._load_or_rebuild()

    def _new_index(self):
        return self._faiss.IndexIDMap(self._faiss.IndexFlatL2(self.DIMENSION))

    def add_employee(
        self,
        employee_id: str,
        name: str,
        samples: list[tuple[str, np.ndarray]],
    ) -> None:
        employee_id = employee_id.strip()
        name = name.strip()
        if not employee_id or not name:
            raise ValueError("Employee ID and name are required")
        if len(samples) != 5:
            raise ValueError("Exactly five pose samples are required")
        poses = [pose for pose, _ in samples]
        if len(set(poses)) != 5:
            raise ValueError("Each of the five pose labels must be unique")

        prepared: list[tuple[str, np.ndarray]] = []
        for pose, vector in samples:
            value = np.asarray(vector, dtype=np.float32).reshape(-1)
            if value.size != self.DIMENSION or not np.isfinite(value).all():
                raise ValueError("Each embedding must be a finite 512-D vector")
            norm = float(np.linalg.norm(value))
            if norm <= 1e-12:
                raise ValueError("Embedding vector cannot be zero")
            prepared.append((pose, value / norm))

        with self.database.connection:
            self.database.connection.execute(
                "INSERT INTO employees(employee_id, name) VALUES (?, ?)",
                (employee_id, name),
            )
            self.database.connection.executemany(
                """INSERT INTO face_embeddings
                   (employee_id, pose, vector, dimension) VALUES (?, ?, ?, ?)""",
                [
                    (employee_id, pose, vector.tobytes(), self.DIMENSION)
                    for pose, vector in prepared
                ],
            )
            self._increment_data_revision()

        rows = self.database.connection.execute(
            """SELECT id, pose FROM face_embeddings
               WHERE employee_id = ? ORDER BY id""",
            (employee_id,),
        ).fetchall()
        vectors_by_pose = {pose: vector for pose, vector in prepared}
        ids = np.asarray([row_id for row_id, _ in rows], dtype=np.int64)
        vectors = np.ascontiguousarray(
            [vectors_by_pose[pose] for _, pose in rows], dtype=np.float32
        )
        try:
            self.index.add_with_ids(vectors, ids)
            self._save_index()
        except Exception:
            # SQLite is the source of truth. Restore a usable in-memory index
            # if an incremental FAISS update fails after the DB transaction.
            logger.exception("Incremental FAISS add failed; rebuilding from SQLite")
            self._rebuild()

    def employee_exists(self, employee_id: str) -> bool:
        row = self.database.connection.execute(
            "SELECT 1 FROM employees WHERE employee_id = ?", (employee_id.strip(),)
        ).fetchone()
        return row is not None

    def remove_employee(self, employee_id: str) -> bool:
        """Delete an employee and remove only that employee's vectors."""
        employee_id = employee_id.strip()
        with self.database.connection:
            exists = self.database.connection.execute(
                "SELECT 1 FROM employees WHERE employee_id = ?", (employee_id,)
            ).fetchone()
            if exists is None:
                return False
            ids = self.database.connection.execute(
                "SELECT id FROM face_embeddings WHERE employee_id = ? ORDER BY id",
                (employee_id,),
            ).fetchall()
            self.database.connection.execute(
                "DELETE FROM employees WHERE employee_id = ?", (employee_id,)
            )
            self._increment_data_revision()

        vector_ids = np.asarray([row[0] for row in ids], dtype=np.int64)
        try:
            if vector_ids.size:
                self.index.remove_ids(vector_ids)
            self._save_index()
        except Exception:
            logger.exception("Incremental FAISS delete failed; rebuilding from SQLite")
            self._rebuild()
        return True

    def search(self, vector: np.ndarray) -> FaceMatch | None:
        if self.index.ntotal == 0:
            return None
        query = np.asarray(vector, dtype=np.float32).reshape(1, -1)
        if query.shape[1] != self.DIMENSION or not np.isfinite(query).all():
            raise ValueError("Search vector must be a finite 512-D vector")
        norm = float(np.linalg.norm(query))
        if norm <= 1e-12:
            raise ValueError("Search vector cannot be zero")
        distances, ids = self.index.search(query / norm, 1)
        distance = float(distances[0, 0])
        vector_id = int(ids[0, 0])
        if vector_id < 0 or distance > self.threshold:
            return None
        row = self.database.connection.execute(
            """SELECT e.employee_id, p.name, e.pose
               FROM face_embeddings e JOIN employees p USING(employee_id)
               WHERE e.id = ?""",
            (vector_id,),
        ).fetchone()
        if row is None:
            # This can happen if another process changed SQLite directly.
            self._load_or_rebuild()
            return None
        employee_id, name, pose = row
        return FaceMatch(employee_id, name, distance, pose)

    def rebuild(self) -> int:
        """Recreate the persisted index from SQLite for manual maintenance."""
        count = self._rebuild()
        if not self._last_save_succeeded:
            raise RuntimeError("Could not persist the rebuilt FAISS index")
        return count

    def _load_or_rebuild(self) -> None:
        if not self.index_path.is_file() or not self._index_revisions_match():
            self._rebuild()
            return

        try:
            loaded = self._faiss.read_index(str(self.index_path))
            if not isinstance(loaded, self._faiss.IndexIDMap):
                raise ValueError("Stored FAISS index has no external IDs")
            if loaded.d != self.DIMENSION:
                raise ValueError(f"Stored FAISS index has dimension {loaded.d}")
            stored_ids = np.asarray(self._faiss.vector_to_array(loaded.id_map))
            database_ids = self._valid_vector_ids()
            if loaded.ntotal != len(database_ids) or set(stored_ids.tolist()) != database_ids:
                raise ValueError("Stored FAISS IDs do not match SQLite embeddings")
            self.index = loaded
        except Exception:
            logger.exception("Stored FAISS index is invalid; rebuilding from SQLite")
            self._rebuild()

    def _valid_vector_ids(self) -> set[int]:
        rows = self.database.connection.execute(
            """SELECT e.id FROM face_embeddings e
               JOIN employees p USING(employee_id)
               WHERE e.dimension = ? AND length(e.vector) = ?
               ORDER BY e.id""",
            (self.DIMENSION, self.DIMENSION * np.dtype(np.float32).itemsize),
        ).fetchall()
        return {int(row[0]) for row in rows}

    def _increment_data_revision(self) -> None:
        self.database.connection.execute(
            "UPDATE vector_index_state SET data_revision = data_revision + 1 WHERE id = 1"
        )

    def _index_revisions_match(self) -> bool:
        row = self.database.connection.execute(
            "SELECT data_revision, index_revision FROM vector_index_state WHERE id = 1"
        ).fetchone()
        return row is not None and int(row[0]) == int(row[1])

    def _save_index(self) -> bool:
        temporary_index = self.index_path.with_suffix(".tmp")
        try:
            self._faiss.write_index(self.index, str(temporary_index))
            temporary_index.replace(self.index_path)
            with self.database.connection:
                self.database.connection.execute(
                    """UPDATE vector_index_state
                       SET index_revision = data_revision WHERE id = 1"""
                )
            self._last_save_succeeded = True
            return True
        except Exception:
            temporary_index.unlink(missing_ok=True)
            self._last_save_succeeded = False
            logger.exception("Could not persist FAISS index; it will be rebuilt on startup")
            return False

    def _rebuild(self) -> int:
        rows = self.database.connection.execute(
            """SELECT e.id, e.employee_id, p.name, e.pose, e.vector, e.dimension
               FROM face_embeddings e JOIN employees p USING(employee_id)
               ORDER BY e.id"""
        ).fetchall()
        self.index = self._new_index()
        vectors: list[np.ndarray] = []
        vector_ids: list[int] = []
        for vector_id, _employee_id, _name, _pose, raw_vector, dimension in rows:
            if dimension != self.DIMENSION:
                continue
            vector = np.frombuffer(raw_vector, dtype=np.float32)
            if vector.size != self.DIMENSION or not np.isfinite(vector).all():
                continue
            vectors.append(vector.copy())
            vector_ids.append(int(vector_id))
        if vectors:
            self.index.add_with_ids(
                np.ascontiguousarray(vectors, dtype=np.float32),
                np.asarray(vector_ids, dtype=np.int64),
            )
        self._save_index()
        return int(self.index.ntotal)
