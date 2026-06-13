#!/usr/bin/env python3
"""Phase 6.3.0 — Inventory Intelligence activation audit with before/after delta."""

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

PHASE_622_BASELINE = {
    "actionable_rate_pct": 100.0,
    "seller_usefulness": 74.1,
    "dashboard_echo_pct": 0.0,
    "coverage_score_pct": 50.0,
    "trustworthiness": 87.5,
    "ai_readiness": 85.7,
}

PHASE_630_PRE_CALIBRATION = {
    "seller_usefulness": 68.2,
    "ai_readiness": 85.3,
    "inventory_insight_rate_pct": 100.0,
}

PHASE_630B_TARGETS = {
    "seller_usefulness": {"min": 74.0},
    "ai_readiness": {"min": 86.0},
    "inventory_insight_rate_pct": {"min": 25.0},
    "dashboard_echo_pct": {"max": 0.0},
    "actionable_rate_pct": {"min": 100.0},
}

INVENTORY_FINDING_PREFIXES = (
    "inventory_dead_stock",
    "inventory_slow_movers",
    "inventory_frozen_capital",
    "inventory_stock_concentration",
    "inventory_risk_high",
)


def build_delta(before: dict, after: dict) -> dict:
    delta: dict[str, float | str] = {}
    for key in before:
        b, a = before.get(key), after.get(key)
        if isinstance(b, (int, float)) and isinstance(a, (int, float)):
            delta[key] = round(float(a) - float(b), 1)
    return delta


def _inventory_insight_rate_from_rows(rows) -> float:
    if not rows:
        return 0.0
    hits = 0
    for rec in rows:
        plan = rec.action_plan or {}
        su = plan.get("seller_usefulness") or plan
        engine = su.get("insight_engine") or plan.get("insight_engine") or {}
        structured = engine.get("structured_insights") or []
        rt = rec.reasoning_trace or {}
        ml = rt.get("multi_layer") or {}
        inv_findings = []
        for o in ml.get("domain_outputs") or []:
            if o.get("analyst_id") == "inventory_analyst":
                inv_findings.extend(f.get("finding_id") or "" for f in o.get("findings") or [])
        text = " ".join(
            [
                rec.title or "",
                rec.summary or "",
                str(plan.get("recommended_action") or ""),
            ]
        ).lower()
        if any(p.replace("_", " ") in text or p in text for p in INVENTORY_FINDING_PREFIXES):
            hits += 1
            continue
        if any(
            prefix in str(item.get("finding_id") or "")
            for item in structured
            if isinstance(item, dict)
            for prefix in INVENTORY_FINDING_PREFIXES
        ):
            hits += 1
            continue
        if any(
            prefix in fid
            for fid in inv_findings
            for prefix in INVENTORY_FINDING_PREFIXES
            if prefix != "inventory_healthy"
        ):
            hits += 1
            continue
        inv_markers = ("мёртв", "мертв", "медленн", "заморож", "остатк", "неликвид", "inventory", "frozen capital")
        if any(m in text for m in inv_markers):
            hits += 1
    return round(hits / len(rows) * 100, 1)


def _inventory_insight_rate(audit: dict) -> float:
    recs = audit.get("recommendations") or []
    if recs:
        hits = 0
        for rec in recs:
            if rec.get("inventory_hit"):
                hits += 1
        return round(hits / len(recs) * 100, 1)
    return 0.0


def _inventory_sub_coverage_from_rows(rows) -> float:
    if not rows:
        return 0.0
    scores: list[float] = []
    for rec in rows:
        plan = rec.action_plan or {}
        su = plan.get("seller_usefulness") or plan
        bc = plan.get("business_coverage") or su.get("business_coverage") or {}
        blocks = bc.get("blocks") or []
        inv = next((b for b in blocks if b.get("block_id") == "inventory_procurement"), None)
        if not inv:
            continue
        subs = inv.get("sub_items") or []
        if not subs:
            continue
        on = sum(1 for s in subs if s.get("available"))
        scores.append(on / len(subs) * 100)
    return round(sum(scores) / len(scores), 1) if scores else 0.0


def enrich_metrics(audit: dict, base: dict, *, rows=None) -> dict:
    out = dict(base)
    if rows is not None:
        out["inventory_insight_rate_pct"] = _inventory_insight_rate_from_rows(rows)
        out["inventory_sub_coverage_pct"] = _inventory_sub_coverage_from_rows(rows)
    else:
        out["inventory_insight_rate_pct"] = _inventory_insight_rate(audit)
        out["inventory_sub_coverage_pct"] = 0.0
    return out


def evaluate_phase_630_targets(metrics: dict) -> dict:
    checks = {
        "seller_usefulness_gte_74": metrics["seller_usefulness"] >= PHASE_630B_TARGETS["seller_usefulness"]["min"],
        "ai_readiness_gte_86": metrics["ai_readiness"] >= PHASE_630B_TARGETS["ai_readiness"]["min"],
        "inventory_insight_rate_gte_25": metrics.get("inventory_insight_rate_pct", 0)
        >= PHASE_630B_TARGETS["inventory_insight_rate_pct"]["min"],
        "dashboard_echo_zero": metrics["dashboard_echo_pct"] <= PHASE_630B_TARGETS["dashboard_echo_pct"]["max"],
        "actionable_rate_100": metrics["actionable_rate_pct"] >= PHASE_630B_TARGETS["actionable_rate_pct"]["min"],
        "inventory_sub_coverage_gte_66": metrics.get("inventory_sub_coverage_pct", 0) >= 66.0,
    }
    return {"decision": "GO" if all(checks.values()) else "NO-GO", "checks": checks, "targets": PHASE_630B_TARGETS}


async def run_phase(
    user_id: UUID,
    *,
    limit: int,
    reset: bool,
    dry_run: bool,
) -> dict:
    recs_before = await load_all_recommendations(user_id)
    audit_before = run_audit(recs_before[:limit])
    metrics_before = enrich_metrics(audit_before, extract_audit_metrics(audit_before), rows=recs_before[:limit])

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
    metrics_after = enrich_metrics(audit_after, extract_audit_metrics(audit_after), rows=recs_after[:limit])

    return {
        "phase": "6.3.0B",
        "user_id": str(user_id),
        "phase_622_baseline": PHASE_622_BASELINE,
        "metrics_before_run": metrics_before,
        "metrics_after": metrics_after,
        "delta_vs_phase_622_baseline": build_delta(PHASE_622_BASELINE, metrics_after),
        "delta_within_run": build_delta(metrics_before, metrics_after),
        "audit_before": audit_before,
        "audit_after": audit_after,
        "phase_630_targets": evaluate_phase_630_targets(metrics_after),
        "migration": {
            "reset_deleted_count": deleted,
            "reports_migrated": len(migration_runs),
            "runs": migration_runs,
        },
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 6.3.0 inventory intelligence audit")
    add_archetype_arguments(parser)
    parser.add_argument("--user-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json-out", default="reports/phase_630_inventory_audit.json")
    parser.add_argument("--skip-migrate", action="store_true", help="Audit current recs only")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    user_id, spec, resolved_limit, warnings = resolve_audit_context(
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

    limit = resolved_limit

    if args.skip_migrate:
        rows = await _load_recommendations(user_id, limit)
        audit = run_audit(rows)
        metrics = enrich_metrics(audit, extract_audit_metrics(audit), rows=rows)
        payload = {
            "phase": "6.3.0B",
            "metrics_after": metrics,
            "delta_vs_phase_622_baseline": build_delta(PHASE_622_BASELINE, metrics),
            "phase_630_targets": evaluate_phase_630_targets(metrics),
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
        ma = payload.get("metrics_after") or {}
        if not ma and "audit" in payload:
            rows_for_val = await _load_recommendations(user_id, limit)
            ma = enrich_metrics(payload["audit"], extract_audit_metrics(payload["audit"]), rows=rows_for_val)
        else:
            rows_for_val = await _load_recommendations(user_id, limit)
        validation = validate_archetype(spec, ma, rows_for_val)
        payload["archetype"] = {
            "id": spec.id,
            "name": spec.name,
            "validation_status": spec.validation_status,
        }
        payload["archetype_validation"] = validation_result_to_dict(validation)
        payload["archetype_warnings"] = warnings

    out_path = Path(args.json_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    ma = payload.get("metrics_after") or {}
    if not ma and "audit" in payload:
        ma = enrich_metrics(payload["audit"], extract_audit_metrics(payload["audit"]))

    print("\n=== Phase 6.3.0B — Priority Calibration Audit ===")
    print(f"{'Metric':<28} {'622 Base':>10} {'After':>10} {'Delta':>10}")
    for key in list(PHASE_622_BASELINE.keys()) + ["inventory_insight_rate_pct", "inventory_sub_coverage_pct"]:
        base = PHASE_622_BASELINE.get(key, 0)
        delta = payload.get("delta_vs_phase_622_baseline", {}).get(key, 0)
        print(f"{key:<28} {base:>10} {ma.get(key, 0):>10} {delta:>+10.1f}")

    targets = payload.get("phase_630_targets") or {}
    print(f"\nPhase 6.3.0 decision: {targets.get('decision', '?')}")
    print(f"Checks: {json.dumps(targets.get('checks', {}), ensure_ascii=False)}")
    if payload.get("archetype_validation"):
        av = payload["archetype_validation"]
        print(f"\nArchetype ({av.get('archetype_id')}): {av.get('overall_decision')}")
    if warnings:
        for w in warnings:
            print(f"WARN: {w}")
    print(f"\nFull report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
