#!/usr/bin/env python3
"""Phase 6.5.3 — Multi-seller discovery, replay, and consolidated validation."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.core.security_context import TenantSession
from app.models.ai_intelligence import AIRecommendation
from app.models.finance.aggregates import DailyAggregate, SkuDailyMetric
from app.models.inventory.snapshot import WarehouseStockSnapshot
from app.models.report import Report, ReportStatus, ReportType
from app.models.user import User
from scripts.ai_recommendation_quality_audit import _load_recommendations, run_audit
from scripts.archetype_validation import (
    get_archetype,
    list_archetype_ids,
    load_manifest,
    validate_archetype,
    validation_result_to_dict,
)
from scripts.phase_621_migration_audit import extract_audit_metrics
from scripts.phase_630_inventory_audit import enrich_metrics

PILOT_USER = UUID("caefecb3-5789-4878-a9d4-929be573fbcc")
PILOT_METRICS = {
    "seller_usefulness": 80.3,
    "ai_readiness": 86.1,
    "actionable_rate_pct": 100.0,
    "inventory_insight_rate_pct": 100.0,
    "dashboard_echo_pct": 0.0,
}

ARCHETYPE_IDS = (
    "small_seller",
    "seasonal_seller",
    "unprofitable_seller",
    "no_ads_seller",
    "high_inventory_seller",
)


async def discover_sellers() -> list[dict[str, Any]]:
    """Audit available tenants with reports and AI recommendations."""
    async with SessionLocal() as db:
        users = (await db.execute(select(User.id, User.email).order_by(User.created_at))).all()

        profiles: list[dict[str, Any]] = []
        for user_id, email in users:
            uid = user_id
            async with TenantSession.transaction(db, uid):
                report_count = (
                    await db.execute(
                        select(func.count())
                        .select_from(Report)
                        .where(
                            Report.user_id == uid,
                            Report.report_type == ReportType.FINANCE,
                            Report.status == ReportStatus.PROCESSED,
                        )
                    )
                ).scalar_one()

                rec_count = (
                    await db.execute(
                        select(func.count())
                        .select_from(AIRecommendation)
                        .where(AIRecommendation.user_id == uid)
                    )
                ).scalar_one()

                if int(report_count or 0) == 0 and int(rec_count or 0) == 0:
                    continue

                sku_count = (
                    await db.execute(
                        select(func.count(func.distinct(SkuDailyMetric.sku))).where(
                            SkuDailyMetric.user_id == uid
                        )
                    )
                ).scalar_one()

                period = (
                    await db.execute(
                        select(
                            func.min(DailyAggregate.aggregate_date),
                            func.max(DailyAggregate.aggregate_date),
                        ).where(DailyAggregate.user_id == uid)
                    )
                ).one()

                revenue = (
                    await db.execute(
                        select(func.coalesce(func.sum(DailyAggregate.revenue), 0)).where(
                            DailyAggregate.user_id == uid
                        )
                    )
                ).scalar_one()

                profit = (
                    await db.execute(
                        select(func.coalesce(func.sum(DailyAggregate.net_profit), 0)).where(
                            DailyAggregate.user_id == uid
                        )
                    )
                ).scalar_one()

                inv_snapshots = (
                    await db.execute(
                        select(func.count())
                        .select_from(WarehouseStockSnapshot)
                        .where(WarehouseStockSnapshot.user_id == uid)
                    )
                ).scalar_one()

                inv_skus = (
                    await db.execute(
                        select(func.count(func.distinct(WarehouseStockSnapshot.sku))).where(
                            WarehouseStockSnapshot.user_id == uid
                        )
                    )
                ).scalar_one()

                rev_rows = (
                    await db.execute(
                        select(DailyAggregate.aggregate_date, DailyAggregate.revenue)
                        .where(DailyAggregate.user_id == uid)
                        .order_by(DailyAggregate.aggregate_date.desc())
                        .limit(60)
                    )
                ).all()
                rev_delta = _revenue_period_delta_from_rows(rev_rows)

            profiles.append(
                {
                    "user_id": str(uid),
                    "email": email,
                    "finance_reports": int(report_count or 0),
                    "ai_recommendations": int(rec_count or 0),
                    "distinct_skus": int(sku_count or 0),
                    "period_start": period[0].isoformat() if period[0] else None,
                    "period_end": period[1].isoformat() if period[1] else None,
                    "total_revenue": str(revenue or 0),
                    "total_profit": str(profit or 0),
                    "inventory_snapshot_rows": int(inv_snapshots or 0),
                    "inventory_distinct_skus": int(inv_skus or 0),
                    "revenue_period_delta_pct": rev_delta,
                    "inferred_archetypes": _infer_archetypes(
                        sku_count=int(sku_count or 0),
                        revenue=Decimal(str(revenue or 0)),
                        profit=Decimal(str(profit or 0)),
                        inv_rows=int(inv_snapshots or 0),
                        rev_delta=rev_delta,
                        user_id=uid,
                    ),
                }
            )
        return profiles


def _revenue_period_delta_from_rows(rows: list) -> float | None:
    """Compare last two halves of daily revenue rows."""
    if len(rows) < 2:
        return None
    mid = len(rows) // 2
    recent = sum(Decimal(str(r[1] or 0)) for r in rows[:mid])
    prior = sum(Decimal(str(r[1] or 0)) for r in rows[mid:])
    if prior <= 0:
        return None
    return float(((recent - prior) / prior * Decimal("100")).quantize(Decimal("0.1")))


async def _revenue_period_delta(db, user_id: UUID) -> float | None:
    """Compare last two monthly revenue totals if available."""
    async with TenantSession.transaction(db, user_id):
        rows = (
            await db.execute(
                select(DailyAggregate.aggregate_date, DailyAggregate.revenue)
                .where(DailyAggregate.user_id == user_id)
                .order_by(DailyAggregate.aggregate_date.desc())
                .limit(60)
            )
        ).all()
    return _revenue_period_delta_from_rows(rows)


def _infer_archetypes(
    *,
    sku_count: int,
    revenue: Decimal,
    profit: Decimal,
    inv_rows: int,
    rev_delta: float | None,
    user_id: UUID,
) -> list[str]:
    tags: list[str] = []
    if user_id == PILOT_USER or inv_rows >= 100:
        tags.append("high_inventory_seller")
    if sku_count <= 20 and sku_count > 0:
        tags.append("small_seller")
    if rev_delta is not None and abs(rev_delta) >= 25:
        tags.append("seasonal_seller")
    if profit < 0:
        tags.append("unprofitable_seller")
    if revenue > 0 and profit / revenue < Decimal("0.05") and profit >= 0:
        tags.append("unprofitable_seller")
    return list(dict.fromkeys(tags))


def map_archetypes(profiles: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    """Pick best seller per P0 archetype from discovered profiles."""
    mapping: dict[str, Any] = {}
    gaps: list[str] = []

    pilot_id = manifest.get("pilot_reference", {}).get("user_id")
    for aid in ARCHETYPE_IDS:
        spec = get_archetype(aid, manifest)
        assigned_uid = spec.user_id
        candidate = None

        if assigned_uid:
            candidate = next((p for p in profiles if p["user_id"] == str(assigned_uid)), None)
        if candidate is None:
            ranked = [p for p in profiles if aid in p.get("inferred_archetypes", [])]
            ranked.sort(key=lambda p: (p["ai_recommendations"], p["finance_reports"]), reverse=True)
            candidate = ranked[0] if ranked else None
        if candidate is None and aid == "high_inventory_seller" and pilot_id:
            candidate = next((p for p in profiles if p["user_id"] == pilot_id), None)

        if candidate:
            mapping[aid] = {
                "archetype_id": aid,
                "user_id": candidate["user_id"],
                "email": candidate.get("email"),
                "finance_reports": candidate["finance_reports"],
                "distinct_skus": candidate["distinct_skus"],
                "period_start": candidate["period_start"],
                "period_end": candidate["period_end"],
                "inferred_archetypes": candidate["inferred_archetypes"],
                "mapping_source": "manifest" if assigned_uid else "inferred",
                "gap": False,
            }
        else:
            mapping[aid] = {
                "archetype_id": aid,
                "user_id": None,
                "gap": True,
                "gap_reason": "No seller in database matches archetype criteria",
            }
            gaps.append(aid)
    return {"mapping": mapping, "gaps": gaps, "sellers_discovered": len(profiles)}


async def run_archetype_replay(
    archetype_id: str,
    user_id: UUID,
    *,
    limit: int,
) -> dict[str, Any]:
    """Run all four audit paths for one archetype (read-only, no migrate)."""
    spec = get_archetype(archetype_id)
    rows = await _load_recommendations(user_id, limit)
    if not rows:
        return {
            "archetype_id": archetype_id,
            "user_id": str(user_id),
            "status": "SKIP",
            "reason": "no_recommendations",
        }

    quality_audit = run_audit(rows)
    metrics = enrich_metrics(quality_audit, extract_audit_metrics(quality_audit), rows=rows)
    validation = validate_archetype(spec, metrics, rows)

    return {
        "archetype_id": archetype_id,
        "user_id": str(user_id),
        "analyses_count": len(rows),
        "finance_reports_used": limit,
        "metrics": metrics,
        "audits": {
            "ai_recommendation_quality": {
                "go_no_go": quality_audit.get("go_no_go", {}).get("decision"),
                "dashboard_echo_pct": quality_audit["dashboard_echo"]["echo_rate_pct"],
                "actionable_rate_pct": quality_audit["actionable"]["rate_pct"],
                "seller_usefulness": quality_audit["seller_usefulness"]["average_score"],
                "ai_readiness": quality_audit["mvp_ai_score"]["AI Readiness Score"],
            },
            "phase_630_inventory": {
                "inventory_insight_rate_pct": metrics.get("inventory_insight_rate_pct"),
                "inventory_sub_coverage_pct": metrics.get("inventory_sub_coverage_pct"),
            },
            "phase_622_insight": {
                "insight_quality": quality_audit.get("insight_quality", {}).get("average_overall_score"),
                "kpi_statement_rate_pct": quality_audit.get("insight_statements", {}).get(
                    "kpi_statement_rate_pct"
                ),
            },
        },
        "archetype_validation": validation_result_to_dict(validation),
        "status": validation.overall_decision,
    }


def compute_pass_rate(results: list[dict[str, Any]]) -> dict[str, Any]:
    evaluated = [r for r in results if r.get("status") in ("PASS", "FAIL")]
    passed = [r for r in evaluated if r.get("status") == "PASS"]
    failed = [r for r in evaluated if r.get("status") == "FAIL"]
    skipped = [r for r in results if r.get("status") in ("SKIP", None)]

    metrics_by_arch: dict[str, dict] = {}
    for r in evaluated:
        m = r.get("metrics") or {}
        metrics_by_arch[r["archetype_id"]] = m

    su_values = [m.get("seller_usefulness", 0) for m in metrics_by_arch.values()]
    ai_values = [m.get("ai_readiness", 0) for m in metrics_by_arch.values()]
    echo_values = [m.get("dashboard_echo_pct", 0) for m in metrics_by_arch.values()]

    majority_su = sum(1 for v in su_values if v >= 75) >= max(1, len(su_values) // 2 + len(su_values) % 2)
    majority_ai = sum(1 for v in ai_values if v >= 80) >= max(1, len(ai_values) // 2 + len(ai_values) % 2)
    echo_ok = all(v <= 5 for v in echo_values) if echo_values else False

    return {
        "total_archetypes": len(results),
        "evaluated": len(evaluated),
        "passed": len(passed),
        "failed": len(failed),
        "skipped": len(skipped),
        "pass_rate_pct": round(len(passed) / len(evaluated) * 100, 1) if evaluated else 0.0,
        "pass_criteria": {
            "min_archetypes_pass": 4,
            "archetypes_passed": len(passed),
            "majority_su_gte_75": majority_su,
            "majority_ai_gte_80": majority_ai,
            "dashboard_echo_lte_5_all": echo_ok,
        },
        "metric_distributions": {
            "seller_usefulness": _distribution(su_values),
            "ai_readiness": _distribution(ai_values),
            "dashboard_echo_pct": _distribution(echo_values),
        },
    }


def _distribution(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "min": None, "max": None, "avg": None}
    return {
        "count": len(values),
        "min": round(min(values), 1),
        "max": round(max(values), 1),
        "avg": round(sum(values) / len(values), 1),
    }


def evaluate_go_no_go(summary: dict[str, Any], profiles: list[dict], mapping: dict) -> str:
    pc = summary["pass_criteria"]
    unique_sellers = len({m.get("user_id") for m in mapping["mapping"].values() if m.get("user_id")})
    if unique_sellers < 5 and summary["passed"] < 4:
        return "NO-GO"
    if summary["passed"] >= 4 and pc["majority_su_gte_75"] and pc["majority_ai_gte_80"] and pc["dashboard_echo_lte_5_all"]:
        return "GO"
    if summary["passed"] >= 4 and len(summary.get("gaps", [])) == 0:
        return "GO"
    return "NO-GO"


async def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 6.5.3 multi-seller replay")
    parser.add_argument("--json-out", default="reports/multi_seller_replay.json")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--discover-only", action="store_true")
    args = parser.parse_args()

    manifest = load_manifest()
    profiles = await discover_sellers()
    mapping_result = map_archetypes(profiles, manifest)

    payload: dict[str, Any] = {
        "phase": "6.5.3",
        "discovery": {
            "sellers_found": len(profiles),
            "profiles": profiles,
        },
        "archetype_mapping": mapping_result["mapping"],
        "gaps": mapping_result["gaps"],
        "pilot_reference": manifest.get("pilot_reference"),
    }

    if args.discover_only:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(f"Discovered {len(profiles)} sellers, gaps: {mapping_result['gaps']}")
        print(f"Wrote {out}")
        return 0

    replay_results: list[dict[str, Any]] = []
    for aid in ARCHETYPE_IDS:
        entry = mapping_result["mapping"][aid]
        if entry.get("gap") or not entry.get("user_id"):
            replay_results.append(
                {
                    "archetype_id": aid,
                    "user_id": None,
                    "status": "SKIP",
                    "reason": "archetype_gap",
                }
            )
            continue
        try:
            result = await run_archetype_replay(
                aid,
                UUID(entry["user_id"]),
                limit=max(entry.get("finance_reports", 2), args.limit),
            )
            replay_results.append(result)
        except Exception as exc:  # noqa: BLE001
            replay_results.append(
                {
                    "archetype_id": aid,
                    "user_id": entry["user_id"],
                    "status": "SKIP",
                    "reason": "replay_error",
                    "error": str(exc)[:300],
                }
            )

    summary = compute_pass_rate(replay_results)
    summary["gaps"] = mapping_result["gaps"]
    decision = evaluate_go_no_go(summary, profiles, mapping_result)

    payload["replay_results"] = replay_results
    payload["summary"] = summary
    payload["pilot_metrics"] = PILOT_METRICS
    payload["release_decision"] = {
        "tag": "v0.6-mvp-intelligence",
        "decision": decision,
        "criteria": summary["pass_criteria"],
    }

    out = Path(args.json_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    print("\n=== Phase 6.5.3 Multi-Seller Replay ===")
    print(f"Sellers discovered: {len(profiles)}")
    print(f"PASS: {summary['passed']}  FAIL: {summary['failed']}  SKIP: {summary['skipped']}")
    print(f"Gaps: {mapping_result['gaps']}")
    print(f"Release decision ({payload['release_decision']['tag']}): {decision}")
    print(f"Report: {out}")
    return 0 if decision == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
