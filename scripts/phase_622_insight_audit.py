#!/usr/bin/env python3
"""Phase 6.2.2 — Insight Engine refactor audit with before/after delta."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ai_recommendation_quality_audit import _load_recommendations, run_audit
from scripts.archetype_validation import (
    add_archetype_arguments,
    resolve_audit_context,
    validate_archetype,
    validation_result_to_dict,
)
from scripts.phase_621_migration_audit import (
    extract_audit_metrics,
    load_all_recommendations,
    migrate_all_reports,
    reset_user_recommendations,
)

PILOT_USER = UUID("caefecb3-5789-4878-a9d4-929be573fbcc")

PHASE_621_BASELINE = {
    "actionable_rate_pct": 100.0,
    "seller_usefulness": 42.5,
    "dashboard_echo_pct": 25.0,
    "coverage_score_pct": 50.0,
    "trustworthiness": 78.8,
    "ai_readiness": 61.6,
    "go_no_go": "NO-GO",
}

PHASE_622_TARGETS = {
    "dashboard_echo_pct": {"max": 10.0},
    "seller_usefulness": {"min": 65.0},
    "ai_readiness": {"min": 75.0},
    "actionable_rate_pct": {"min": 80.0},
}


def build_delta(before: dict, after: dict) -> dict:
    delta: dict[str, float | str] = {}
    for key in before:
        if key == "go_no_go":
            delta[key] = f"{before[key]} → {after[key]}"
            continue
        b, a = before[key], after[key]
        if isinstance(b, (int, float)) and isinstance(a, (int, float)):
            delta[key] = round(float(a) - float(b), 1)
    return delta


def evaluate_phase_622_targets(metrics: dict) -> dict:
    checks = {
        "dashboard_echo_lte_10": metrics["dashboard_echo_pct"] <= PHASE_622_TARGETS["dashboard_echo_pct"]["max"],
        "seller_usefulness_gte_65": metrics["seller_usefulness"] >= PHASE_622_TARGETS["seller_usefulness"]["min"],
        "ai_readiness_gte_75": metrics["ai_readiness"] >= PHASE_622_TARGETS["ai_readiness"]["min"],
        "actionable_rate_gte_80": metrics["actionable_rate_pct"] >= PHASE_622_TARGETS["actionable_rate_pct"]["min"],
    }
    return {
        "decision": "GO" if all(checks.values()) else "NO-GO",
        "checks": checks,
        "targets": PHASE_622_TARGETS,
    }


async def run_phase(
    user_id: UUID,
    *,
    limit: int,
    reset: bool,
    dry_run: bool,
) -> dict:
    recs_before = await load_all_recommendations(user_id)
    audit_before = run_audit(recs_before[:limit])
    metrics_before = extract_audit_metrics(audit_before)

    deleted = 0
    migration_runs: list[dict] = []
    if reset and not dry_run:
        deleted = await reset_user_recommendations(user_id)
        migration_runs = await migrate_all_reports(user_id)
    elif reset and dry_run:
        deleted = await reset_user_recommendations(user_id, dry_run=True)
        migration_runs = await migrate_all_reports(user_id, dry_run=True)

    recs_after = await load_all_recommendations(user_id)
    audit_after = run_audit(recs_after[:limit])
    metrics_after = extract_audit_metrics(audit_after)

    baseline_delta = build_delta(PHASE_621_BASELINE, metrics_after)
    run_delta = build_delta(metrics_before, metrics_after)

    return {
        "phase": "6.2.2",
        "user_id": str(user_id),
        "phase_621_baseline": PHASE_621_BASELINE,
        "metrics_before_run": metrics_before,
        "metrics_after": metrics_after,
        "delta_vs_phase_621_baseline": baseline_delta,
        "delta_within_run": run_delta,
        "insight_statements_before": audit_before.get("insight_statements"),
        "insight_statements_after": audit_after.get("insight_statements"),
        "insight_quality_before": audit_before.get("insight_quality"),
        "insight_quality_after": audit_after.get("insight_quality"),
        "audit_before": audit_before,
        "audit_after": audit_after,
        "phase_622_targets": evaluate_phase_622_targets(metrics_after),
        "migration": {
            "reset_deleted_count": deleted,
            "reports_migrated": len(migration_runs),
            "runs": migration_runs,
        },
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 6.2.2 insight engine audit")
    add_archetype_arguments(parser)
    parser.add_argument("--user-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json-out", default="reports/phase_622_insight_audit.json")
    parser.add_argument("--skip-migrate", action="store_true", help="Audit current recs only")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    user_id, spec, limit, warnings = resolve_audit_context(
        archetype_id=args.archetype,
        user_id=UUID(args.user_id) if args.user_id else None,
        limit=args.limit,
        manifest_path=manifest_path,
    )
    if user_id is None and not args.archetype:
        user_id = PILOT_USER
    if user_id is None:
        print("ERROR: --user-id required or use --archetype with assigned tenant")
        for w in warnings:
            print(f"  {w}")
        return 2

    if args.skip_migrate:
        rows = await _load_recommendations(user_id, limit)
        audit = run_audit(rows)
        metrics = extract_audit_metrics(audit)
        payload = {
            "phase": "6.2.2",
            "metrics_after": metrics,
            "delta_vs_phase_621_baseline": build_delta(PHASE_621_BASELINE, metrics),
            "insight_statements": audit.get("insight_statements"),
            "insight_quality": audit.get("insight_quality"),
            "phase_622_targets": evaluate_phase_622_targets(metrics),
            "audit": audit,
        }
    else:
        payload = await run_phase(
            user_id,
            limit=limit,
            reset=True,
            dry_run=args.dry_run,
        )

    if spec is not None:
        ma = payload.get("metrics_after") or extract_audit_metrics(payload.get("audit") or {})
        rows_for_val = await _load_recommendations(user_id, limit)
        validation = validate_archetype(spec, ma, rows_for_val)
        payload["archetype"] = {"id": spec.id, "name": spec.name, "validation_status": spec.validation_status}
        payload["archetype_validation"] = validation_result_to_dict(validation)
        payload["archetype_warnings"] = warnings

    out_path = Path(args.json_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    ma = payload.get("metrics_after") or payload.get("metrics_after_run") or {}
    if not ma and "audit" in payload:
        ma = extract_audit_metrics(payload["audit"])

    print("\n=== Phase 6.2.2 — Insight Engine Audit ===")
    print(f"{'Metric':<24} {'621 Base':>10} {'After':>10} {'Delta':>10}")
    for key in PHASE_621_BASELINE:
        if key == "go_no_go":
            print(f"{key:<24} {PHASE_621_BASELINE[key]:>10} {ma.get(key, '?'):>10}")
        else:
            delta = payload.get("delta_vs_phase_621_baseline", {}).get(key, 0)
            print(f"{key:<24} {PHASE_621_BASELINE[key]:>10} {ma.get(key, 0):>10} {delta:>+10.1f}")

    targets = payload.get("phase_622_targets") or {}
    print(f"\nPhase 6.2.2 decision: {targets.get('decision', '?')}")
    print(f"Checks: {json.dumps(targets.get('checks', {}), ensure_ascii=False)}")
    if payload.get("archetype_validation"):
        av = payload["archetype_validation"]
        print(f"\nArchetype ({av.get('archetype_id')}): {av.get('overall_decision')}")

    ins = payload.get("insight_statements_after") or payload.get("insight_statements") or {}
    if ins:
        print(
            f"\nKPI Statements: {ins.get('kpi_statement_rate_pct')}% | "
            f"Insights: {ins.get('insight_statement_rate_pct')}% | "
            f"Echo flags: {ins.get('echo_detected_rate_pct')}%"
        )
    iq = payload.get("insight_quality_after") or payload.get("insight_quality") or {}
    if iq:
        print(f"Insight Quality Score: {iq.get('average_overall_score')}")

    print(f"\nFull report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
