from __future__ import annotations
from app.errors import AppError
from app.infrastructure.database import Database, EXPECTED_TABLES


class TableRepository:
    def __init__(self, database: Database, table: str, key: str = "id", order: str = "created_at"):
        self.database = database
        self.table = table
        self.key = key
        self.order = order
        self.columns = ",".join(column for column in EXPECTED_TABLES[table].split(",") if column != "api_key_hash")

    def _row(self, query) -> dict:
        rows = self.database.execute(query)
        if not rows:
            raise AppError(404, "NOT_FOUND", "The requested record was not found.")
        return rows[0]

    def list(self, options: dict) -> dict:
        limit, offset = options["limit"], options["offset"]
        query = self.database.client.table(self.table).select(self.columns).order(self.order, desc=True).order(self.key)
        for column, value in options.items():
            if column not in {"limit", "offset"}:
                query = query.eq(column, value)
        rows = self.database.execute(query.range(offset, offset + limit))
        return {"items": rows[:limit], "limit": limit, "offset": offset, "has_more": len(rows) > limit}
    
    def list_all(self, filters: dict) -> list[dict]:
        items = []
        offset = 0

        while True:
            query = (
                self.database.client.table(self.table)
                .select(self.columns)
                .order(self.key)
            )
            for column, value in filters.items():
                query = query.eq(column, value)

            rows = self.database.execute(
                query.range(offset, offset + 999)
            )
            if not rows:
                break

            items.extend(rows)
            offset += len(rows)

        return items
    def get(self, record_id: str) -> dict:
        return self._row(self.database.client.table(self.table).select(self.columns).eq(self.key, record_id).limit(1))

    def insert(self, values: dict) -> dict:
        return self._row(self.database.client.table(self.table).insert(values).select(self.columns))

    def update(self, record_id: str, values: dict) -> dict:
        return self._row(self.database.client.table(self.table).update(values).eq(self.key, record_id).select(self.columns))

    def remove(self, record_id: str) -> None:
        self._row(self.database.client.table(self.table).delete().eq(self.key, record_id).select(self.columns))


class EmbeddingRepository(TableRepository):
    def __init__(self, database: Database):
        super().__init__(database, "face_embeddings", "user_id", "updated_at")

    def upsert(self, values: dict) -> dict:
        return self._row(self.database.client.table(self.table).upsert(values, on_conflict="user_id").select(self.columns))


class SessionRepository(TableRepository):
    def __init__(self, database: Database):
        super().__init__(database, "registration_sessions")

    def finalize(self, record_id: str, values: dict, now: str) -> dict:
        query = self.database.client.table(self.table).update(values).eq("id", record_id).eq("status", "pending").gt("expires_at", now)
        rows = self.database.execute(query.select(self.columns))
        if not rows:
            raise AppError(409, "SESSION_NOT_PENDING", "The session is expired or has already been finalized.")
        return rows[0]


class Repositories:
    def __init__(self, database: Database):
        self.users = TableRepository(database, "users")
        self.devices = TableRepository(database, "devices")
        self.embeddings = EmbeddingRepository(database)
        self.sessions = SessionRepository(database)
        self.logs = TableRepository(database, "access_logs", order="access_time")
