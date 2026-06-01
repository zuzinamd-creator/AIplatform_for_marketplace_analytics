#!/usr/bin/env python3
"""
Lightweight architecture governance checks (no external framework).

Usage:
  python scripts/architecture_governance_check.py

Exit code 1 on hard violations; warnings printed for soft checks.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
DOCS_ARCH = ROOT / "docs" / "architecture"
README = ROOT / "README.md"
ALEMBIC_VERSIONS = ROOT / "alembic" / "versions"
LOC_LIMIT = 200
LOC_SCAN_DIRS = ("app/services", "app/etl", "app/core")
LOC_GRANDFATHER = {
    "app/etl/pipeline.py",
    "app/etl/wb/inventory_consistency_verification.py",
    "app/operations/recovery.py",
}

ADR_GOVERNED_PREFIXES = (
    "app/ai/",
    "app/runtime/",
    "app/core/queue/",
    "app/core/inventory_rebuild_lock.py",
    "app/core/security_context.py",
    "app/etl/wb/full_inventory_rebuild.py",
    "app/etl/wb/inventory_snapshot_rebuild.py",
    "app/etl/wb/inventory_snapshot_store.py",
    "app/etl/wb/inventory_ledger_streaming.py",
    "app/etl/wb/persist.py",
    "app/etl/pipeline.py",
    "app/etl/worker.py",
    "app/domain/semantics/",
    "app/domain/inventory/",
    "app/parsers/wb/semantics_registry.py",
    "alembic/versions/",
)

BYPASS_RLS_ALLOWLIST = {
    "app/core/security_context.py",
    "app/core/tenant_context.py",
}

REQUIRED_AI_DOCS = (
    "docs/ai/ai_architecture.md",
    "docs/ai/ai_architecture_report.md",
    "docs/ai/ai_governance.md",
    "docs/ai/ai_lifecycle.md",
    "docs/ai/agent_model.md",
    "docs/ai/prompt_contracts.md",
    "docs/ai/ai_safety.md",
    "docs/ai/ai_operations.md",
    "docs/ai/evaluation_framework.md",
    "docs/ai/decision_engine.md",
    "docs/ai/multi_agent_architecture.md",
    "docs/ai/explainability.md",
    "docs/ai/recommendation_governance.md",
    "docs/ai/evaluation_strategy.md",
    "docs/ai/strategic_memory.md",
)

REQUIRED_ARCHITECTURE_DOCS = (
    "docs/architecture/domain_map.md",
    "docs/architecture/ownership_model.md",
    "docs/architecture/dependency_rules.md",
    "docs/architecture/platform_layers.md",
    "docs/architecture/extension_contracts.md",
    "docs/architecture/invariants.md",
    "docs/architecture/boundaries.md",
)

# (source path prefix, forbidden import prefix, allowlist rel paths)
LAYER_IMPORT_RULES: list[tuple[str, str, frozenset[str]]] = [
    ("app/domain/", "app.api", frozenset()),
    ("app/domain/", "app.services", frozenset()),
    (
        "app/domain/",
        "app.etl",
        frozenset({"app/domain/inventory/analytics_payload.py"}),
    ),
    ("app/domain/", "app.operations", frozenset()),
    ("app/domain/", "sqlalchemy", frozenset()),
    ("app/parsers/", "app.api", frozenset()),
    ("app/parsers/", "app.services", frozenset()),
    ("app/parsers/", "app.etl", frozenset()),
    ("app/parsers/", "sqlalchemy", frozenset()),
    ("app/core/queue/", "app.domain", frozenset()),
    ("app/core/queue/", "app.etl", frozenset()),
    ("app/core/queue/", "app.services", frozenset()),
    ("app/core/queue/", "app.api", frozenset()),
    ("app/api/", "app.etl.wb", frozenset()),
    ("app/api/", "app.etl.worker", frozenset()),
    ("app/api/", "app.etl.pipeline", frozenset()),
    ("app/ai/", "app.etl", frozenset()),
    ("app/ai/", "app.operations.recovery", frozenset()),
    ("app/ai/", "app.runtime.rebuild_dispatcher", frozenset()),
    ("app/services/", "app.etl.pipeline", frozenset()),
    ("app/services/", "app.etl.worker", frozenset()),
    ("app/api/", "app.operations.recovery", frozenset()),
    ("app/runtime/", "app.api", frozenset()),
]

LAYER_IMPORT_WARNINGS: list[tuple[str, str, frozenset[str]]] = []

GOVERNED_MODULE_TESTS: list[tuple[str, tuple[str, ...]]] = [
    (
        "app/ai/",
        (
            "tests/unit/test_ai_governance.py",
            "tests/unit/test_ai_providers.py",
            "tests/unit/test_ai_validation.py",
            "tests/unit/test_ai_prompt_regression.py",
            "tests/unit/test_ai_safety_controls.py",
            "tests/integration/test_ai_execution.py",
            "tests/integration/test_ai_analytics_api.py",
            "tests/unit/test_ai_decision_engine.py",
            "tests/unit/test_ai_multi_agent.py",
            "tests/unit/test_ai_intelligence_governance.py",
            "tests/integration/test_ai_intelligence_api.py",
        ),
    ),
    (
        "app/runtime/",
        (
            "tests/unit/test_rebuild_dispatcher.py",
            "tests/unit/test_runtime_health.py",
            "tests/unit/test_runtime_policy.py",
            "tests/unit/test_runtime_scheduling.py",
            "tests/unit/test_runtime_autonomy_safety.py",
            "tests/unit/test_adaptive_prioritizer.py",
            "tests/integration/test_orchestration_dispatch.py",
            "tests/integration/test_runtime_control_plane.py",
            "tests/unit/test_circuit_breaker.py",
            "tests/unit/test_reliability_kill_switches.py",
            "tests/unit/test_queue_overload_simulation.py",
            "tests/integration/test_reliability_chaos.py",
            "tests/unit/test_enterprise_decision_engine.py",
            "tests/unit/test_enterprise_governance.py",
            "tests/unit/test_enterprise_forecasting.py",
            "tests/integration/test_enterprise_runtime_api.py",
        ),
    ),
    (
        "app/operations/",
        (
            "tests/unit/test_rebuild_orchestration.py",
            "tests/unit/test_recovery_and_safety.py",
            "tests/integration/test_recovery_primitives.py",
        ),
    ),
    (
        "app/core/invariants/",
        ("tests/unit/test_platform_invariants.py",),
    ),
]

REQUIRED_STABILIZATION_DOC = "docs/architecture/stabilization_report.md"

REQUIRED_RUNTIME_DOCS = (
    "docs/runtime/control_plane.md",
    "docs/runtime/runtime_lifecycle.md",
    "docs/runtime/operational_policies.md",
    "docs/runtime/runtime_autonomy_report.md",
    "docs/runtime/autonomy_governance.md",
    "docs/runtime/reliability_model.md",
    "docs/runtime/failure_containment.md",
    "docs/runtime/runtime_resilience.md",
    "docs/runtime/runtime_event_taxonomy.md",
    "docs/runtime/production_readiness.md",
    "docs/runtime/maintenance_mode.md",
    "docs/runtime/autonomous_operations.md",
    "docs/runtime/runtime_strategy.md",
    "docs/runtime/autonomous_governance.md",
    "docs/runtime/scheduling_model.md",
    "docs/runtime/self_healing.md",
    "docs/runtime/operational_forecasting.md",
)

FORBIDDEN_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "blocking advisory lock",
        re.compile(r"pg_advisory_lock\s*\("),
        "Use pg_try_advisory_xact_lock (ADR-002).",
    ),
    (
        "SystemSession in API",
        re.compile(r"from\s+app\.core\.security_context\s+import\s+.*SystemSession"),
        "SystemSession is for migrations only.",
    ),
    (
        "raw commit in API",
        re.compile(r"await\s+db\.commit\s*\("),
        "API must use TenantSession.transaction, not raw commit.",
    ),
]


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _count_code_lines(path: Path) -> int:
    lines = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines += 1
    return lines


def check_loc_warnings() -> list[str]:
    warnings: list[str] = []
    for sub in LOC_SCAN_DIRS:
        base = ROOT / sub
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            rel = _rel(path)
            n = _count_code_lines(path)
            if n > LOC_LIMIT and rel not in LOC_GRANDFATHER:
                warnings.append(f"LOC>{LOC_LIMIT}: {rel} ({n} lines)")
    return warnings


def _import_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped.startswith("from ") or stripped.startswith("import "):
            lines.append(stripped)
    return lines


def check_required_docs() -> list[str]:
    errors: list[str] = []
    for rel in REQUIRED_ARCHITECTURE_DOCS:
        if not (ROOT / rel).is_file():
            errors.append(f"Missing required architecture doc: {rel}")
    for rel in REQUIRED_AI_DOCS:
        if not (ROOT / rel).is_file():
            errors.append(f"Missing required AI doc: {rel}")
    if not (ROOT / REQUIRED_STABILIZATION_DOC).is_file():
        errors.append(f"Missing stabilization report: {REQUIRED_STABILIZATION_DOC}")
    for rel in REQUIRED_RUNTIME_DOCS:
        if not (ROOT / rel).is_file():
            errors.append(f"Missing required runtime doc: {rel}")
    return errors


def check_layer_imports() -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    import_re = re.compile(r"^(?:from|import)\s+([\w.]+)")

    for path in APP.rglob("*.py"):
        rel = _rel(path)
        text = path.read_text(encoding="utf-8")
        for line in _import_lines(text):
            match = import_re.match(line)
            if not match:
                continue
            module = match.group(1)
            for src_prefix, forbidden, allowlist in LAYER_IMPORT_RULES:
                if not rel.startswith(src_prefix):
                    continue
                if rel in allowlist:
                    continue
                if module == forbidden or module.startswith(forbidden + "."):
                    errors.append(
                        f"{rel}: layer violation import '{module}' "
                        f"(forbidden under {src_prefix})"
                    )
            for src_prefix, warn_prefix, allowlist in LAYER_IMPORT_WARNINGS:
                if not rel.startswith(src_prefix) or rel in allowlist:
                    continue
                if module.startswith(warn_prefix):
                    warnings.append(
                        f"{rel}: legacy import '{module}' — do not extend "
                        f"(see dependency_rules.md)"
                    )
    return errors, warnings


def check_governed_module_tests() -> list[str]:
    warnings: list[str] = []
    for prefix, required_tests in GOVERNED_MODULE_TESTS:
        has_code = any(
            _rel(p).startswith(prefix) for p in APP.rglob("*.py") if p.name != "__init__.py"
        )
        if not has_code:
            continue
        missing = [t for t in required_tests if not (ROOT / t).is_file()]
        if missing:
            warnings.append(
                f"Governed prefix {prefix} missing test file(s): {', '.join(missing)}"
            )
    return warnings


def check_forbidden_patterns() -> list[str]:
    errors: list[str] = []
    for path in APP.rglob("*.py"):
        rel = _rel(path)
        text = path.read_text(encoding="utf-8")
        for name, pattern, hint in FORBIDDEN_PATTERNS:
            if "SystemSession in API" in name and not rel.startswith("app/api/"):
                continue
            if "raw commit in API" in name and not rel.startswith("app/api/"):
                continue
            if pattern.search(text):
                errors.append(f"{rel}: forbidden pattern '{name}' — {hint}")
        if rel not in BYPASS_RLS_ALLOWLIST and "alembic" not in rel:
            if re.search(r"set_bypass_rls_context\s*\(\s*[^,]+,\s*True", text):
                errors.append(
                    f"{rel}: set_bypass_rls_context(True) outside allowlist — TEN-NO-BYPASS"
                )
    return errors


def _git_changed_files() -> list[str] | None:
    for base in ("origin/main", "origin/master", "HEAD~1"):
        try:
            out = subprocess.check_output(
                ["git", "diff", "--name-only", base],
                cwd=ROOT,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            if out.strip():
                return [line.strip() for line in out.splitlines() if line.strip()]
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", "--cached"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return [line.strip() for line in out.splitlines() if line.strip()] or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def check_adr_governed_diff(changed: list[str] | None) -> list[str]:
    if not changed:
        return []
    warnings: list[str] = []
    governed = [p for p in changed if any(p.startswith(prefix) for prefix in ADR_GOVERNED_PREFIXES)]
    if not governed:
        return []
    adr_touched = any(p.startswith("docs/architecture/adr/") for p in changed)
    readme_touched = "README.md" in changed
    if not adr_touched and not readme_touched:
        warnings.append(
            "ADR-governed paths changed without docs/architecture/adr/ or README update: "
            + ", ".join(governed[:5])
            + ("..." if len(governed) > 5 else "")
        )
    return warnings


def check_migration_readme(changed: list[str] | None) -> list[str]:
    if not changed:
        return []
    new_migrations = [
        p
        for p in changed
        if p.startswith("alembic/versions/") and p.endswith(".py") and " __" not in p
    ]
    if not new_migrations:
        return []
    if not README.is_file():
        return ["README.md missing — cannot verify migration documentation"]
    readme_text = README.read_text(encoding="utf-8")
    warnings: list[str] = []
    for mig in new_migrations:
        stem = Path(mig).stem
        rev = stem.split("_", 1)[0]
        if rev not in readme_text and stem not in readme_text:
            warnings.append(
                f"Migration {mig} not mentioned in README.md (§18 Alembic expected)"
            )
    return warnings


def main() -> int:
    print("Architecture governance check")
    errors = check_required_docs()
    errors.extend(check_forbidden_patterns())
    import_errors, import_warnings = check_layer_imports()
    errors.extend(import_errors)
    warnings: list[str] = list(import_warnings)
    warnings.extend(check_governed_module_tests())
    warnings.extend(check_loc_warnings())
    changed = _git_changed_files()
    if changed:
        print(f"Git diff: {len(changed)} file(s)")
    warnings.extend(check_adr_governed_diff(changed))
    warnings.extend(check_migration_readme(changed))

    for w in warnings:
        print(f"WARNING: {w}")
    for e in errors:
        print(f"ERROR: {e}")

    if errors:
        print(f"\nFailed: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"\nOK ({len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
