import httpx
from postgrest.exceptions import APIError
from supabase import create_client
from supabase.client import ClientOptions

from app.config import Settings
from app.errors import AppError, database_error

EXPECTED_TABLES = {
    "users": "id,user_code,full_name,email,phone,department,role,status,created_at,updated_at",
    "devices": "id,device_code,name,location,api_key_hash,status,settings,last_seen_at,created_at",
    "face_embeddings": "user_id,image_url,model_name,model_version,dimension,embedding_data,updated_at",
    "registration_sessions": "id,user_id,device_id,status,expires_at,created_at,completed_at",
    "access_logs": "id,user_id,device_id,result,confidence,access_time,synced_at",
}


class Database:
    def __init__(self, settings: Settings):
        self.transport = httpx.Client(timeout=settings.timeout_ms / 1000, follow_redirects=False)
        self.client = create_client(settings.supabase_url, settings.secret_key, ClientOptions(
            schema="public", persist_session=False, auto_refresh_token=False, httpx_client=self.transport,
        ))

    def execute(self, query):
        try:
            return query.retry(False).execute().data
        except APIError as error:
            raise database_error(error.code) from None
        except httpx.HTTPError:
            raise database_error("") from None

    def check(self) -> list[dict]:
        report = []
        for table, columns in EXPECTED_TABLES.items():
            try:
                self.client.table(table).select(columns, head=True).limit(1).retry(False).execute()
            except (APIError, httpx.HTTPError):
                raise AppError(503, "DATABASE_UNAVAILABLE", f"Database readiness failed for public.{table}; check connectivity, credentials and schema.") from None
            report.append({"table": table, "ok": True})
        return report

    def close(self):
        self.transport.close()
