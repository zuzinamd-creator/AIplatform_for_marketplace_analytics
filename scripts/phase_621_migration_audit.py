#!/usr/bin/env python3
"""Phase 6.2.1 — full recommendation migration and true AI readiness audit."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.core.security_context import TenantSession
from app.dto.ai_analytics_dto import AIRunRequestDTO, AnalyticsWorkflow
from app.models.ai_intelligence import AIRecommendation, AIRecommendationFeedback
from app.models.report import Report, ReportStatus, ReportType
from app.services.ai_service import AIService
from scripts.ai_recommendation_quality_audit import _load_recommendations, run_audit

PILOT_USER = UUID("caefecb3-5789-4878-a9d4-929be573fbcc")


@dataclass(frozen=True)
class PipelineClassification:
    recommendation_id: str
    report_id: str | None
    is_new_pipeline: bool
    has_source_period: bool
    has_business_coverage: bool
    has_executive_summary_v2: bool
    has_root_cause_confidence: bool
    insight_engine_version: str | None


def classify_recommendation_pipeline(rec: AIRecommendation) -> PipelineClassification:
    plan = rec.action_plan or {}
    su = plan.get("seller_usefulness") or plan
    bc = plan.get("business_coverage") or su.get("business_coverage") or {}
    if not isinstance(bc, dict):
        bc = {}

    has_period = bool(plan.get("source_period_start") or su.get("source_period_start"))
    has_coverage = bc.get("business_coverage_score") is not None
    has_exec_v2 = bool(
        plan.get("executive_summary_v2")
        or su.get("executive_summary_v2")
        or bc.get("executive_summary_v2")
    )
    has_root = bool(
        plan.get("root_cause_confidence")
        or su.get("root_cause_confidence")
        or bc.get("root_cause_confidence")
    )
    lineage = rec.lineage or {}
    engine_ver = lineage.get("insight_engine_version")
    is_new = has_period and has_coverage and has_exec_v2 and has_root

    return PipelineClassification(
        recommendation_id=str(rec.id),
        report_id=lineage.get("report_id"),
        is_new_pipeline=is_new,
        has_source_period=has_period,
        has_business_coverage=has_coverage,
        has_executive_summary_v2=has_exec_v2,
        has_root_cause_confidence=has_root,
        insight_engine_version=str(engine_ver) if engine_ver else None,
    )


async def load_all_recommendations(user_id: UUID) -> list[AIRecommendation]:
    async with SessionLocal() as db:
        async with TenantSession.transaction(db, user_id):
            return list(
                (
                    await db.execute(
                        select(AIRecommendation)
                        .where(AIRecommendation.user_id == user_id)
                        .order_by(AIRecommendation.created_at.desc())
                    )
                ).scalars().all()
            )


async def load_finance_reports(user_id: UUID) -> list[Report]:
    async with SessionLocal() as db:
        async with TenantSession.transaction(db, user_id):
            return list(
                (
                    await db.scalars(
                        select(Report)
                        .where(
                            Report.user_id == user_id,
                            Report.report_type == ReportType.FINANCE,
                            Report.status == ReportStatus.PROCESSED,
                        )
                        .order_by(Report.created_at)
                    )
                ).all()
            )


def build_pipeline_inventory_report(
    recs: list[AIRecommendation],
    reports: list[Report],
) -> dict:
    classified = [classify_recommendation_pipeline(r) for r in recs]
    new_count = sum(1 for c in classified if c.is_new_pipeline)
    legacy_count = len(classified) - new_count
    total = len(classified) or 1

    return {
        "total_recommendations": len(classified),
        "new_pipeline_count": new_count,
        "legacy_pipeline_count": legacy_count,
        "legacy_share_pct": round(legacy_count / total * 100, 1),
        "new_pipeline_share_pct": round(new_count / total * 100, 1),
        "processed_finance_reports": len(reports),
        "recommendations_per_report": len(classified) / max(len(reports), 1),
        "new_pipeline_criteria": {
            "source_period_start": True,
            "business_coverage_score": True,
            "executive_summary_v2": True,
            "root_cause_confidence": True,
        },
        "samples": [
            {
                "recommendation_id": c.recommendation_id,
                "report_id": c.report_id,
                "pipeline": "period_intelligence" if c.is_new_pipeline else "legacy",
                "flags": {
                    "source_period": c.has_source_period,
                    "business_coverage": c.has_business_coverage,
                    "executive_summary_v2": c.has_executive_summary_v2,
                    "root_cause_confidence": c.has_root_cause_confidence,
                    "insight_engine_version": c.insight_engine_version,
                },
            }
            for c in classified
        ],
    }


async def reset_user_recommendations(user_id: UUID, *, dry_run: bool = False) -> int:
    async with SessionLocal() as db:
        async with TenantSession.transaction(db, user_id):
            rec_ids = list(
                await db.scalars(select(AIRecommendation.id).where(AIRecommendation.user_id == user_id))
            )
            if dry_run:
                return len(rec_ids)
            if rec_ids:
                await db.execute(
                    delete(AIRecommendationFeedback).where(
                        AIRecommendationFeedback.user_id == user_id,
                        AIRecommendationFeedback.recommendation_id.in_(rec_ids),
                    )
                )
                await db.execute(
                    delete(AIRecommendation).where(AIRecommendation.user_id == user_id)
                )
            await db.commit()
            return len(rec_ids)


async def migrate_all_reports(user_id: UUID, *, dry_run: bool = False) -> list[dict]:
    reports = await load_finance_reports(user_id)
    results: list[dict] = []
    for report in reports:
        entry = {"report_id": str(report.id), "status": "pending"}
        if dry_run:
            entry["status"] = "dry_run"
            results.append(entry)
            continue
        request = AIRunRequestDTO(
            workflow=AnalyticsWorkflow.REVENUE_INSIGHT,
            prompt_id="analytics.summary.v1",
            semantics_version="1.0",
            report_id=report.id,
        )
        async with SessionLocal() as db:
            result = await AIService(db, user_id).run_intelligence(request)
        entry["status"] = "ok"
        entry["recommendation_id"] = str(result.recommendation_id)
        results.append(entry)
    return results


def extract_audit_metrics(report: dict) -> dict:
    mvp = report.get("mvp_ai_score") or {}
    return {
        "actionable_rate_pct": report["actionable"]["rate_pct"],
        "seller_usefulness": report["seller_usefulness"]["average_score"],
        "dashboard_echo_pct": report["dashboard_echo"]["echo_rate_pct"],
        "coverage_score_pct": report["business_coverage_report"]["average_score_pct"],
        "trustworthiness": mvp.get("Trustworthiness", 0.0),
        "ai_readiness": mvp.get("AI Readiness Score", 0.0),
        "go_no_go": report["go_no_go"]["decision"],
        "analyses_count": report["analyses_count"],
        "samples_with_coverage": report["business_coverage_report"]["samples_with_coverage"],
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


async def run_phase(
    user_id: UUID,
    *,
    limit: int,
    reset: bool,
    dry_run: bool,
) -> dict:
    recs_before = await load_all_recommendations(user_id)
    reports = await load_finance_reports(user_id)
    inventory_before = build_pipeline_inventory_report(recs_before, reports)

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
    inventory_after = build_pipeline_inventory_report(recs_after, reports)
    audit_after = run_audit(recs_after[:limit])
    metrics_after = extract_audit_metrics(audit_after)

    return {
        "user_id": str(user_id),
        "pipeline_inventory_before": inventory_before,
        "pipeline_inventory_after": inventory_after,
        "audit_before": audit_before,
        "audit_after": audit_after,
        "metrics_before": metrics_before,
        "metrics_after": metrics_after,
        "delta": build_delta(metrics_before, metrics_after),
        "migration": {
            "reset_deleted_count": deleted,
            "reports_migrated": len(migration_runs),
            "runs": migration_runs,
        },
        "go_no_go_decision": metrics_after["go_no_go"],
        "go_no_go_basis": "post_migration_only",
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 6.2.1 migration + audit")
    parser.add_argument("--user-id", default=str(PILOT_USER))
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json-out", default="reports/phase_621_migration_audit.json")
    parser.add_argument("--skip-migrate", action="store_true", help="Inventory + before audit only")
    args = parser.parse_args()

    user_id = UUID(args.user_id)

    if args.skip_migrate:
        recs = await load_all_recommendations(user_id)
        reports = await load_finance_reports(user_id)
        payload = {
            "pipeline_inventory": build_pipeline_inventory_report(recs, reports),
            "metrics_before": extract_audit_metrics(run_audit(recs[: args.limit])),
        }
    else:
        payload = await run_phase(
            user_id,
            limit=args.limit,
            reset=True,
            dry_run=args.dry_run,
        )

    out_path = Path(args.json_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    if args.skip_migrate:
        inv = payload["pipeline_inventory"]
        print(f"Total recs: {inv['total_recommendations']}")
        print(f"Legacy: {inv['legacy_pipeline_count']} ({inv['legacy_share_pct']}%)")
        print(f"New pipeline: {inv['new_pipeline_count']} ({inv['new_pipeline_share_pct']}%)")
        return 0

    print("\n=== TASK 1 — Pipeline inventory (before) ===")
    inv = payload["pipeline_inventory_before"]
    print(
        f"Total: {inv['total_recommendations']} | Legacy: {inv['legacy_pipeline_count']} "
        f"({inv['legacy_share_pct']}%) | New: {inv['new_pipeline_count']} ({inv['new_pipeline_share_pct']}%)"
    )
    print(f"Processed finance reports: {inv['processed_finance_reports']}")

    mb, ma = payload["metrics_before"], payload["metrics_after"]
    print("\n=== TASK 4 — Metrics ===")
    print(f"{'Metric':<22} {'Before':>10} {'After':>10} {'Delta':>10}")
    for key in mb:
        if key == "go_no_go":
            print(f"{key:<22} {mb[key]:>10} {ma[key]:>10} {payload['delta'][key]:>10}")
        else:
            print(f"{key:<22} {mb[key]:>10} {ma[key]:>10} {payload['delta'][key]:>+10.1f}")

    print("\n=== TASK 5 — GO/NO-GO (post-migration only) ===")
    print(f"Decision: {payload['go_no_go_decision']}")
    print(f"Checks: {json.dumps(payload['audit_after']['go_no_go']['checks'], ensure_ascii=False)}")
    print(f"\nFull report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
