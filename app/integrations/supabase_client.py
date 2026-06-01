from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings


@lru_cache
def get_supabase_client() -> Client | None:
    """Supabase client for storage and future platform features."""
    if not settings.supabase_url or not settings.supabase_key:
        return None
    return create_client(settings.supabase_url, settings.supabase_key)


def upload_report_file(user_id: str, report_id: str, filename: str, content: bytes) -> str | None:
    """
    Optional: upload raw report to Supabase Storage.
    Returns storage path or None if client/bucket not configured.
    """
    client = get_supabase_client()
    if client is None:
        return None

    path = f"{user_id}/{report_id}/{filename}"
    bucket = settings.supabase_storage_bucket
    client.storage.from_(bucket).upload(
        path,
        content,
        file_options={"content-type": "application/octet-stream", "upsert": "true"},
    )
    return f"{bucket}/{path}"
