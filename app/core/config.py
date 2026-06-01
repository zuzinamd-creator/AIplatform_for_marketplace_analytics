from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Marketplace Analytics API"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    database_url: str
    # Optional: password outside URL (avoids @ : / breaking urlparse)
    database_password: str = ""
    # Optional extra CA (e.g. corporate SSL inspection root); verification stays enabled
    database_ssl_extra_ca_file: str = ""
    environment_mode: str = "LOCAL_DEV"  # LOCAL_DEV | INTEGRATION | MAIN

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    supabase_url: str = ""
    supabase_key: str = ""
    supabase_storage_bucket: str = "reports"

    # Alembic only — never used by API/worker runtime paths
    alembic_bypass_rls: bool = True

    job_max_attempts: int = 3
    job_visibility_timeout_seconds: int = 1800

    storage_backend: str = "supabase"
    allow_local_storage_fallback: bool = False
    uploads_dir: str = "uploads"
    max_upload_bytes: int = 52_428_800
    upload_spool_max_bytes: int = 10_485_760

    log_level: str = "INFO"
    worker_heartbeat_interval_seconds: int = 15

    # Production safety guards (structured log thresholds only)
    ops_rebuild_duration_warn_ms: int = 120_000
    ops_wal_bytes_delta_warn: int = 500_000_000
    ops_queue_lag_warn_seconds: int = 1800
    ops_anomaly_window_hours: int = 24
    ops_anomaly_count_warn: int = 500
    ops_drift_window_hours: int = 24
    ops_drift_fail_warn: int = 50
    recovery_stale_running_seconds: int = 3600
    recovery_staging_older_than_seconds: int = 86_400

    # Runtime orchestrator (rebuild dispatcher process)
    orchestrator_enabled: bool = True
    orchestrator_poll_interval_seconds: float = 5.0
    orchestrator_dispatch_batch_size: int = 20
    orchestrator_max_dispatch_per_cycle: int = 1
    orchestrator_defer_busy_seconds: int = 60
    orchestrator_maintenance_every_cycles: int = 12
    orchestrator_max_cycles_per_run: int = 0  # 0 = unlimited (until shutdown)
    orchestrator_runaway_rebuilds_per_hour: int = 30

    # Runtime control plane / autonomy (Phase 3)
    runtime_autonomy_enabled: bool = True
    runtime_max_autonomous_actions_per_cycle: int = 3
    runtime_queue_overload_threshold: int = 500
    runtime_rebuild_backlog_warn: int = 50
    runtime_max_concurrent_rebuilds_global: int = 32
    runtime_starvation_idle_cycles: int = 60
    runtime_incremental_to_full_after_attempts: int = 3
    runtime_ai_pause_when_overloaded: bool = True
    runtime_enterprise_ops_enabled: bool = True
    runtime_autonomy_safety_level: str = "standard"

    # Production reliability (Phase A)
    worker_enabled: bool = True
    maintenance_mode: bool = False
    reliability_circuit_failure_threshold: int = 5
    reliability_circuit_recovery_seconds: int = 60
    reliability_process_heartbeat_interval_seconds: int = 15
    reliability_process_stale_seconds: int = 120
    reliability_orchestrator_lease_ttl_seconds: int = 30
    reliability_tenant_quarantine_dlq_threshold: int = 10
    reliability_tenant_throttle_pending_jobs: int = 200
    reliability_tenant_throttle_duration_seconds: int = 300
    reliability_global_dlq_warn_threshold: int = 50
    reliability_rebuild_storm_per_hour: int = 40
    reliability_ai_runaway_per_hour: int = 100
    ai_failover_provider: str = ""

    # AI execution layer (governed, advisory-only)
    ai_enabled: bool = True
    ai_default_token_budget: int = 8000
    ai_execution_timeout_seconds: int = 120
    ai_request_timeout_seconds: int = 60
    ai_stale_rebuild_pending_warn: int = 5
    ai_provider: str = "mock"
    ai_openai_base_url: str = ""
    ai_openai_api_key: str = ""
    ai_openai_model: str = "gpt-4o-mini"
    ai_failover_api_key: str = ""
    ai_failover_base_url: str = ""
    ai_failover_model: str = ""
    ai_reasoning_model: str = ""
    ai_fast_model: str = ""
    ai_cheap_model: str = ""
    ai_enable_streaming: bool = True
    ai_enable_cost_tracking: bool = True
    ai_max_cost_per_run_usd: float = 0.50
    ai_max_cost_per_day_usd: float = 25.0
    ai_enable_response_cache: bool = False
    ai_cache_ttl_seconds: int = 300
    ai_prompt_runtime_version: str = "v3"
    ai_provider_max_retries: int = 2
    ai_max_retries: int = 2
    ai_rate_limit_per_minute: int = 30
    ai_memory_max_turns: int = 10
    ai_disabled_agents: str = ""

    @property
    def async_database_url(self) -> str:
        from app.core.asyncpg_connect import resolve_database_url

        return resolve_database_url(self.database_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # populated from environment


def reload_settings() -> Settings:
    """Reload .env-backed settings (clears lru_cache). Call after editing .env."""
    get_settings.cache_clear()
    import app.core.config as config_module

    config_module.settings = get_settings()
    return config_module.settings


settings = get_settings()
