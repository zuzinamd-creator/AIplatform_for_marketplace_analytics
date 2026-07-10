"""Unit tests for scripts/production-recovery.sh (mocked externals, no DB/curl/alembic)."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RECOVERY_SH_SRC = REPO_ROOT / "scripts" / "production-recovery.sh"


def _write_executable(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _setup_recovery_workspace(
    tmp_path: Path,
    *,
    alembic_script: str,
    git_head: str = "c6187fe497ee52fbb7228e0dcc2b077ab50023cc",
) -> Path:
    """Copy recovery script into tmp repo root so ROOT resolves under tmp_path."""
    scripts = tmp_path / "scripts"
    lib = scripts / "lib"
    venv_bin = tmp_path / ".venv" / "bin"
    fake_bin = tmp_path / "fake-bin"

    scripts.mkdir(parents=True)
    shutil.copy(RECOVERY_SH_SRC, scripts / "production-recovery.sh")

    _write_executable(
        scripts / "preflight-env.sh",
        "#!/usr/bin/env bash\nexit 0\n",
    )
    _write_executable(
        lib / "deploy-guard.sh",
        "#!/usr/bin/env bash\ndeploy_guard_check() { return 0; }\n",
    )
    alembic_body = (
        alembic_script
        if alembic_script.startswith("#!")
        else "#!/usr/bin/env bash\n" + alembic_script
    )
    _write_executable(venv_bin / "alembic", alembic_body)

    (tmp_path / ".env").write_text("SECRET_KEY=test\n", encoding="utf-8")

    _write_executable(
        fake_bin / "curl",
        """#!/usr/bin/env bash
if [[ "$1" == "-sk" && "$2" == "-o" ]]; then
  echo "200"
  exit 0
fi
if [[ "$1" == "-sk" ]]; then
  echo '{"status":"ok"}'
  exit 0
fi
exit 1
""",
    )
    _write_executable(
        fake_bin / "hostname",
        "#!/usr/bin/env bash\necho test-host\n",
    )
    _write_executable(
        fake_bin / "git",
        f"""#!/usr/bin/env bash
if [[ "$1" == "rev-parse" && "$2" == "HEAD" ]]; then
  echo "{git_head}"
  exit 0
fi
if [[ "$1" == "status" ]]; then
  exit 0
fi
exit 0
""",
    )

    return fake_bin


def _run_recovery(
    tmp_path: Path,
    fake_bin: Path,
    extra_env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"
    env["BACKUP_ENV"] = str(tmp_path / "missing-backup.env")
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(tmp_path / "scripts" / "production-recovery.sh"), "--assess-only"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
        check=False,
    )


def test_default_certified_sha_is_production_baseline() -> None:
    text = RECOVERY_SH_SRC.read_text(encoding="utf-8")
    assert "certified-production" in text
    assert "74e7fff65664d4cc87118b621b2dc8221c1bf09e" not in text
    assert "b4a8497e35f95ff5599221ada82d4d212e2fc056" not in text
    assert "11731e911a16c92b9aeea8c6bafb533cf49e245b" not in text
    assert "83daf8c43673344ccba8735ff5b95fb60c4d4e6c" not in text
    assert "01cfee975f05eb1824be181634950914b31d3577" not in text
    assert "9301e5e76bd82e7cc1b69e6514c0a8f15c65b10b" not in text


def test_recovery_certified_sha_match_reaches_summary(tmp_path: Path) -> None:
    fake_bin = _setup_recovery_workspace(
        tmp_path,
        alembic_script='echo "0035_registration_invites (head)"\n',
    )
    result = _run_recovery(tmp_path, fake_bin)
    assert "=== Assessment summary ===" in result.stdout
    assert "  OK   HEAD matches certified baseline" in result.stdout
    assert "  OK   alembic code head=0035_registration_invites" in result.stdout
    assert "  result: ASSESS OK" in result.stdout
    assert result.returncode == 0


def test_recovery_head_mismatch_exit_one(tmp_path: Path) -> None:
    fake_bin = _setup_recovery_workspace(
        tmp_path,
        alembic_script='echo "0035_registration_invites (head)"\n',
    )
    result = _run_recovery(
        tmp_path,
        fake_bin,
        {"CERTIFIED_SHA": "0000000000000000000000000000000000000000"},
    )
    assert "=== Assessment summary ===" in result.stdout
    assert "  FAIL HEAD" in result.stdout
    assert "  result: NEEDS ATTENTION" in result.stdout
    assert result.returncode == 1


def test_recovery_alembic_failure_reaches_summary(tmp_path: Path) -> None:
    fake_bin = _setup_recovery_workspace(
        tmp_path,
        alembic_script="exit 2\n",
    )
    result = _run_recovery(tmp_path, fake_bin)
    assert "=== Assessment summary ===" in result.stdout
    assert "  FAIL alembic heads unavailable or empty" in result.stdout
    assert "--- Deploy guard (dry) ---" in result.stdout
    assert "  result: NEEDS ATTENTION" in result.stdout
    assert result.returncode == 1


def test_recovery_alembic_success_with_override_sha(tmp_path: Path) -> None:
    fake_bin = _setup_recovery_workspace(
        tmp_path,
        alembic_script='echo "0042_example (head)"\n',
        git_head="abcdef1234567890abcdef1234567890abcdef12",
    )
    result = _run_recovery(
        tmp_path,
        fake_bin,
        {"CERTIFIED_SHA": "abcdef1234567890abcdef1234567890abcdef12"},
    )
    assert "=== Assessment summary ===" in result.stdout
    assert "  OK   alembic code head=0042_example" in result.stdout
    assert result.returncode == 0
