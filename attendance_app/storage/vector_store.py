"""Persistent local FAISS vector index backed by SQLite enrollment records."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from config.settings import APP_ROOT, FACE_MATCH_THRESHOLD
from storage.database import FaceDatabase


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

    def search(self, vector: np.ndarray) -> FaceMatch | None: ...


class FaissVectorStore:
    """Exact squared-L2 search over normalized embeddings, persisted offline."""

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
        self.index = faiss.IndexFlatL2(self.DIMENSION)
        self._metadata: list[tuple[str, str, str]] = []
        self._rebuild()

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
        self._rebuild()

    def search(self, vector: np.ndarray) -> FaceMatch | None:
        if self.index.ntotal == 0:
            return None
        query = np.asarray(vector, dtype=np.float32).reshape(1, -1)
        if query.shape[1] != self.DIMENSION or not np.isfinite(query).all():
            raise ValueError("Search vector must be a finite 512-D vector")
        norm = float(np.linalg.norm(query))
        if norm <= 1e-12:
            raise ValueError("Search vector cannot be zero")
        distances, indices = self.index.search(query / norm, 1)
        distance = float(distances[0, 0])
        index_position = int(indices[0, 0])
        if index_position < 0 or distance > self.threshold:
            return None
        employee_id, name, pose = self._metadata[index_position]
        return FaceMatch(employee_id, name, distance, pose)

    def _rebuild(self) -> None:
        rows = self.database.connection.execute(
            """SELECT e.employee_id, p.name, e.pose, e.vector, e.dimension
               FROM face_embeddings e JOIN employees p USING(employee_id)
               ORDER BY e.id"""
        ).fetchall()
        self.index = self._faiss.IndexFlatL2(self.DIMENSION)
        self._metadata = []
        vectors: list[np.ndarray] = []
        for employee_id, name, pose, raw_vector, dimension in rows:
            if dimension != self.DIMENSION:
                continue
            vector = np.frombuffer(raw_vector, dtype=np.float32)
            if vector.size != self.DIMENSION or not np.isfinite(vector).all():
                continue
            vectors.append(vector.copy())
            self._metadata.append((employee_id, name, pose))
        if vectors:
            self.index.add(np.ascontiguousarray(vectors, dtype=np.float32))
        temporary_index = self.index_path.with_suffix(".tmp")
        try:
            self._faiss.write_index(self.index, str(temporary_index))
            temporary_index.replace(self.index_path)
        except (OSError, RuntimeError):
            # SQLite stores the source vectors; the FAISS file can be rebuilt
            # on next startup if persisting this local index fails.
            temporary_index.unlink(missing_ok=True)
