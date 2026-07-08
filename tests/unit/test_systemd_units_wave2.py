"""Wave 2 systemd unit file checks (Phase 8.2.0)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SYSTEMD_DIR = ROOT / "deploy" / "systemd"
PREFLIGHT_EXEC_START_PRE = (
    "ExecStartPre=/root/AIplatform_for_marketplace_analytics/scripts/preflight-env.sh --systemd"
)


def _read_unit(name: str) -> str:
    return (SYSTEMD_DIR / name).read_text(encoding="utf-8")


def test_backend_unit_has_exec_start_pre() -> None:
    content = _read_unit("marketplace-backend.service")
    assert PREFLIGHT_EXEC_START_PRE in content


def test_worker_unit_has_exec_start_pre() -> None:
    content = _read_unit("marketplace-worker.service")
    assert PREFLIGHT_EXEC_START_PRE in content


def test_orchestrator_unit_exists_with_exec_start_pre() -> None:
    path = SYSTEMD_DIR / "marketplace-orchestrator.service"
    assert path.is_file()
    content = path.read_text(encoding="utf-8")
    assert PREFLIGHT_EXEC_START_PRE in content
    assert "app.runtime.orchestration_worker" in content
