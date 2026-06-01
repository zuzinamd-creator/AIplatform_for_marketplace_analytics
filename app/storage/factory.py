from functools import lru_cache

from app.core.config import settings
from app.integrations.supabase_client import get_supabase_client
from app.storage.local_storage import LocalReportStorage
from app.storage.protocol import ReportStorage
from app.storage.supabase_storage import SupabaseReportStorage


@lru_cache
def get_report_storage() -> ReportStorage:
    """
    Primary: Supabase/S3 when configured.
    Fallback: local uploads only for explicit dev mode or missing credentials.
    """
    if settings.storage_backend == "local":
        return LocalReportStorage()

    if settings.storage_backend == "supabase":
        if settings.allow_local_storage_fallback:
            # Local demo/docker: skip remote bucket (uploads volume) even when Supabase URL is set.
            return LocalReportStorage()
        if get_supabase_client() is not None:
            return SupabaseReportStorage()
        raise RuntimeError(
            "Supabase storage is required. Configure SUPABASE_URL and SUPABASE_KEY."
        )

    if settings.allow_local_storage_fallback:
        return LocalReportStorage()

    raise RuntimeError(
        "No storage backend available. Configure remote storage or enable local fallback."
    )
