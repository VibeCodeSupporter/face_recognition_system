"""Local SQLite persistence for offline face enrollment and embeddings."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from config.settings import APP_ROOT


class FaceDatabase:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else APP_ROOT / "data" / "faces.sqlite3"
        self.path = self.path.expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.path))
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS employees (
                employee_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS face_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
                pose TEXT NOT NULL,
                vector BLOB NOT NULL,
                dimension INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(employee_id, pose)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS vector_index_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                data_revision INTEGER NOT NULL DEFAULT 0,
                index_revision INTEGER NOT NULL DEFAULT -1
            )"""
        )
        self.connection.execute(
            """INSERT OR IGNORE INTO vector_index_state
               (id, data_revision, index_revision) VALUES (1, 0, -1)"""
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()
