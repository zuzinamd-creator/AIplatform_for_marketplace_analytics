"""Shell integration tests for scripts/lib/deploy-guard.sh."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / "scripts" / "lib" / "deploy-guard.sh"


def _run_guard(repo: Path, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    base_env = {k: v for k, v in os.environ.items() if k != "GITHUB_ACTIONS"}
    full_env = {**base_env, **(env or {})}
    script = f"""
set -euo pipefail
source "{GUARD}"
deploy_guard_check "{repo}"
"""
    return subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env=full_env,
        check=False,
    )


def test_deploy_guard_clean_tree(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "README.md").write_text("ok\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)

    result = _run_guard(repo)
    assert result.returncode == 0, result.stderr


def test_deploy_guard_blocks_dirty_app(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "README.md").write_text("ok\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)
    app_dir = repo / "app"
    app_dir.mkdir()
    (app_dir / "main.py").write_text("# change\n")

    result = _run_guard(repo)
    assert result.returncode == 1
    assert "DEPLOY GUARD FAIL" in result.stderr


def test_deploy_guard_allows_tsbuildinfo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "README.md").write_text("ok\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)
    frontend = repo / "frontend"
    frontend.mkdir()
    (frontend / "tsconfig.app.tsbuildinfo").write_text("{}\n")

    result = _run_guard(repo)
    assert result.returncode == 0, result.stderr


def test_deploy_guard_bypass_force_dirty(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "README.md").write_text("ok\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)
    (repo / "dirty.txt").write_text("x\n")

    result = _run_guard(repo, env={"DEPLOY_FORCE_DIRTY": "1"})
    assert result.returncode == 0
    assert "bypassed" in result.stderr.lower()


def test_deploy_guard_skips_in_github_actions(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / "dirty.txt").write_text("x\n")

    result = _run_guard(repo, env={"GITHUB_ACTIONS": "true"})
    assert result.returncode == 0
