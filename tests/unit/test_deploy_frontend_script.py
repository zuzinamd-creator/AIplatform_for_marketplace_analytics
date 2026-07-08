"""Unit tests for scripts/deploy-frontend.sh deploy guard integration."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPLOY_SH_SRC = REPO_ROOT / "scripts" / "deploy-frontend.sh"
GUARD_SH_SRC = REPO_ROOT / "scripts" / "lib" / "deploy-guard.sh"


def _write_executable(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _init_git_repo(repo: Path, *, extra_files: dict[str, str] | None = None) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "README.md").write_text("ok\n", encoding="utf-8")
    if extra_files:
        for rel, body in extra_files.items():
            target = repo / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)


def _setup_deploy_workspace(tmp_path: Path) -> tuple[Path, Path]:
    """Copy deploy script + guard into tmp repo; fake systemctl/free on PATH."""
    scripts = tmp_path / "scripts"
    lib = scripts / "lib"
    frontend = tmp_path / "frontend"
    fake_bin = tmp_path / "fake-bin"

    scripts.mkdir(parents=True)
    lib.mkdir(parents=True)
    frontend.mkdir(parents=True)
    shutil.copy(DEPLOY_SH_SRC, scripts / "deploy-frontend.sh")
    shutil.copy(GUARD_SH_SRC, lib / "deploy-guard.sh")

    _write_executable(
        fake_bin / "systemctl",
        """#!/usr/bin/env bash
exit 0
""",
    )
    _write_executable(
        fake_bin / "free",
        """#!/usr/bin/env bash
echo "Mem: 2048 512 1024 64 512 1536 800"
""",
    )
    _write_executable(
        fake_bin / "pkill",
        "#!/usr/bin/env bash\nexit 0\n",
    )
    _write_executable(
        fake_bin / "flock",
        "#!/usr/bin/env bash\nexit 0\n",
    )

    return scripts, fake_bin


def _run_deploy(
    tmp_path: Path,
    fake_bin: Path,
    *,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    run_env = os.environ.copy()
    run_env["PATH"] = f"{fake_bin}:{run_env.get('PATH', '')}"
    run_env["LOCK_FILE"] = f"/tmp/frontend-deploy-test-{os.getpid()}-{id(tmp_path)}.lock"
    run_env["FRONTEND_SERVICE"] = "marketplace-frontend.service"
    run_env["DEPLOY_MIN_FREE_MB"] = "300"
    if env:
        run_env.update(env)
    return subprocess.run(
        ["bash", str(tmp_path / "scripts" / "deploy-frontend.sh")],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=run_env,
        check=False,
    )


@pytest.mark.parametrize(
    ("dirty_rel", "dirty_body", "extra_env", "expect_pass"),
    [
        (None, None, None, True),
        ("app/dirty.py", "# uncommitted\n", None, False),
        ("app/dirty.py", "# uncommitted\n", {"DEPLOY_FORCE_DIRTY": "1"}, True),
    ],
    ids=["clean_tree", "dirty_tree", "force_dirty_bypass"],
)
def test_deploy_frontend_guard_tree(
    tmp_path: Path,
    dirty_rel: str | None,
    dirty_body: str | None,
    extra_env: dict[str, str] | None,
    expect_pass: bool,
) -> None:
    _setup_deploy_workspace(tmp_path)
    _init_git_repo(tmp_path)
    if dirty_rel and dirty_body:
        path = tmp_path / dirty_rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dirty_body, encoding="utf-8")

    env = dict(extra_env or {})
    result = _run_deploy(tmp_path, tmp_path / "fake-bin", env=env)

    if expect_pass:
        assert "DEPLOY GUARD FAIL" not in result.stderr
        assert "=== Deploy guard (git tree + RAM) ===" in result.stdout
        assert "=== Pre-deploy: stop" in result.stdout
    else:
        assert result.returncode == 1
        assert "DEPLOY GUARD FAIL" in result.stderr
        assert "=== Pre-deploy: stop" not in result.stdout


def test_deploy_frontend_guard_allows_tsbuildinfo(tmp_path: Path) -> None:
    _setup_deploy_workspace(tmp_path)
    _init_git_repo(tmp_path)
    (tmp_path / "frontend" / "tsconfig.app.tsbuildinfo").write_text("{}\n", encoding="utf-8")

    result = _run_deploy(tmp_path, tmp_path / "fake-bin")
    assert "DEPLOY GUARD FAIL" not in result.stderr
    assert "=== Pre-deploy: stop" in result.stdout
