"""Tests for scripts/preflight-env.sh (file checks only, no DB)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT_SH = ROOT / "scripts" / "preflight-env.sh"


def test_preflight_env_missing_file(tmp_path: Path) -> None:
    env_file = tmp_path / "missing.env"
    result = subprocess.run(
        ["bash", str(PREFLIGHT_SH), "--check"],
        capture_output=True,
        text=True,
        env={"ENV_FILE": str(env_file)},
        check=False,
        cwd=ROOT,
    )
    assert result.returncode == 1
    assert "PREFLIGHT FAIL" in result.stderr


def test_preflight_env_unreadable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("SECRET_KEY=x\nDATABASE_URL=y\n")
    env_file.chmod(0o000)
    try:
        result = subprocess.run(
            ["bash", str(PREFLIGHT_SH), "--check"],
            capture_output=True,
            text=True,
            env={"ENV_FILE": str(env_file)},
            check=False,
            cwd=ROOT,
        )
    finally:
        env_file.chmod(0o644)
    assert result.returncode == 1
    assert "unreadable" in result.stderr.lower()


@pytest.mark.skipif(not (ROOT / ".env").is_file(), reason="requires workspace .env for integration")
def test_preflight_env_check_with_workspace_env() -> None:
    result = subprocess.run(
        ["bash", str(PREFLIGHT_SH), "--check"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    assert result.returncode == 0, result.stderr
