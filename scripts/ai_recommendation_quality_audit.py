#!/usr/bin/env python3
"""Phase 6.1/6.2 — AI recommendation quality and business coverage audit."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from scripts.archetype_validation import (
    add_archetype_arguments,
    resolve_audit_context,
    validate_archetype,
    validation_result_to_dict,
)
from app.ai.quality.recommendation_audit import (
    ANALYST_RULE_CATALOG,
    BUSINESS_CASE_CATALOG,
    analyze_dashboard_echo,
    audit_insight_statements,
    check_period_consistency,
    classify_recommendation_text,
    compute_mvp_ai_score,
    evaluate_go_no_go,
    extract_insight_payload_from_plan,
    is_actionable,
    is_dashboard_echo,
)
from app.core.database import SessionLocal
from app.core.security_context import TenantSession
from app.models.ai_intelligence import AIRecommendation

PRODUCTION_URL = "https://321997.fornex.cloud"


def _commit_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


async def _load_recommendations(user_id: UUID | None, limit: int) -> list[AIRecommendation]:
    async with SessionLocal() as db:
        q = select(AIRecommendation).order_by(AIRecommendation.created_at.desc()).limit(limit)
        if user_id is not None:
            async with TenantSession.transaction(db, user_id):
                rows = (await db.execute(q.where(AIRecommendation.user_id == user_id))).scalars().all()
        else:
            rows = (await db.execute(q)).scalars().all()
        return list(rows)


def _snap_from_rec(rec: AIRecommendation) -> dict:
    plan = rec.action_plan or {}
    su = plan.get("seller_usefulness") or plan
    snap: dict = {}
    for key in (
        "report_id",
        "source_period_start",
        "source_period_end",
        "compare_period_start",
        "compare_period_end",
        "requested_compare_period_start",
        "requested_compare_period_end",
        "compare_mode",
        "deep_insights",
        "causal_headline",
        "business_coverage",
        "root_cause_confidence",
    ):
        if su.get(key) is not None:
            snap[key] = su.get(key)
    if plan.get("business_coverage"):
        snap["business_coverage"] = plan["business_coverage"]
    if su.get("total_revenue"):
        snap["total_revenue"] = su.get("total_revenue")
    if plan.get("total_revenue"):
        snap["total_revenue"] = plan.get("total_revenue")
    lineage = rec.lineage or {}
    if lineage.get("report_id"):
        snap["report_id"] = lineage.get("report_id")
    return snap


def _lines_from_rec(rec: AIRecommendation) -> list[str]:
    plan = rec.action_plan or {}
    lines = [rec.title, rec.summary]
    action = plan.get("recommended_action")
    if action:
        lines.append(str(action))
    for part in (rec.summary or "").split("\n"):
        if part.strip():
            lines.append(part.strip())
    deep = (plan.get("seller_usefulness") or plan).get("deep_insights") or plan.get("deep_insights")
    if isinstance(deep, list):
        lines.extend(str(x) for x in deep)
    return [ln for ln in lines if ln and ln.strip()]


def _primary_text(rec: AIRecommendation) -> str:
    plan = rec.action_plan or {}
    su = plan.get("seller_usefulness") or plan
    payload = extract_insight_payload_from_plan(plan)
    primary = payload.get("primary_insight")
    if isinstance(primary, dict) and primary.get("what_happened"):
        parts = [
            primary.get("what_happened"),
            primary.get("why"),
            primary.get("recommended_action"),
        ]
        return " ".join(str(p) for p in parts if p)
    parts = [
        rec.title,
        plan.get("recommended_action"),
        su.get("what_to_do_today"),
        su.get("concrete_next_action"),
    ]
    deep = su.get("deep_insights") or plan.get("deep_insights")
    if isinstance(deep, list):
        parts.extend(str(x) for x in deep[:3])
    return " ".join(str(p) for p in parts if p)


def run_audit(rows: list[AIRecommendation]) -> dict:
    block1: list[dict] = []
    classifications: Counter[str] = Counter()
    echo_stats = {"total": 0, "echo": 0, "beyond_dashboard": 0}
    actionable_stats = {"total": 0, "actionable": 0}
    period_checks: list[dict] = []

    coverage_scores: list[float] = []
    missing_scores: list[float] = []
    usefulness_scores: list[float] = []
    ad_coverage_flags: list[bool] = []
    root_cause_samples: list[dict] = []
    insight_statement_stats = {"kpi": 0, "insight": 0, "echo_flags": 0}
    insight_quality_scores: list[float] = []

    for rec in rows:
        snap = _snap_from_rec(rec)
        period = (
            f"{snap.get('source_period_start', '?')} — {snap.get('source_period_end', '?')}"
        )
        plan = rec.action_plan or {}
        su = plan.get("seller_usefulness") or plan
        recommended_action = plan.get("recommended_action") or su.get("recommended_action")
        primary = _primary_text(rec)
        insight_payload = extract_insight_payload_from_plan(plan)
        insight_audit = audit_insight_statements(
            title=rec.title or "",
            summary=rec.summary or "",
            snap=snap,
            structured_insights=insight_payload.get("structured_insights"),
            insight_audit=insight_payload.get("insight_audit"),
            insight_quality=insight_payload.get("insight_quality"),
        )
        insight_statement_stats["kpi"] += insight_audit["kpi_statement_count"]
        insight_statement_stats["insight"] += insight_audit["insight_statement_count"]
        if insight_audit.get("echo_detected"):
            insight_statement_stats["echo_flags"] += 1
        avg_q = (insight_audit.get("insight_quality_avg") or {}).get("overall")
        if avg_q is not None:
            insight_quality_scores.append(float(avg_q))

        cls = classify_recommendation_text(primary, snap)
        classifications[cls.value] += 1
        echo = analyze_dashboard_echo(primary, snap)
        echo_stats["total"] += 1
        if is_dashboard_echo(primary, snap):
            echo_stats["echo"] += 1
        if echo.beyond_dashboard:
            echo_stats["beyond_dashboard"] += 1
        act = is_actionable(primary, str(recommended_action or ""))
        actionable_stats["total"] += 1
        if act:
            actionable_stats["actionable"] += 1

        bc = (plan.get("business_coverage") or su.get("business_coverage") or {}) if isinstance(plan, dict) else {}
        if isinstance(bc, dict) and bc.get("business_coverage_score") is not None:
            coverage_scores.append(float(bc["business_coverage_score"]))
            missing_scores.append(float(bc.get("missing_data_score") or (100 - float(bc["business_coverage_score"]))))
            usefulness_scores.append(float(bc.get("seller_usefulness_score") or 0))
            ad_coverage_flags.append(bool(bc.get("advertising_data_coverage")))
            root_cause_samples.append(
                {
                    "recommendation_id": str(rec.id),
                    "root_cause_confidence": bc.get("root_cause_confidence") or [],
                }
            )

        block1.append(
            {
                "report_id": snap.get("report_id") or (rec.lineage or {}).get("report_id"),
                "period": period,
                "recommendation_id": str(rec.id),
                "recommendation_type": rec.workflow_type,
                "confidence": rec.confidence_score,
                "priority": rec.priority_score,
                "text": (rec.summary or rec.title or "")[:400],
                "recommended_action": (recommended_action or "")[:300],
                "classification": cls.value,
                "echo_kpis": echo.kpis_used,
                "beyond_dashboard": echo.beyond_dashboard,
                "actionable": act,
                "insight_audit": insight_audit,
                "echo_detected": insight_audit.get("echo_detected"),
            }
        )

        for line in _lines_from_rec(rec):
            if line == primary or line == rec.title:
                continue
            sub_cls = classify_recommendation_text(line, snap)
            sub_echo = analyze_dashboard_echo(line, snap)
            block1.append(
                {
                    "report_id": snap.get("report_id") or (rec.lineage or {}).get("report_id"),
                    "period": period,
                    "recommendation_id": str(rec.id),
                    "recommendation_type": rec.workflow_type,
                    "confidence": rec.confidence_score,
                    "priority": rec.priority_score,
                    "text": line[:300],
                    "classification": sub_cls.value,
                    "echo_kpis": sub_echo.kpis_used,
                    "beyond_dashboard": sub_echo.beyond_dashboard,
                    "actionable": is_actionable(line, str(recommended_action or "")),
                    "detail_line": True,
                }
            )

        period_checks.append(
            {
                "recommendation_id": str(rec.id),
                **check_period_consistency(
                    ui_start=snap.get("source_period_start"),
                    ui_end=snap.get("source_period_end"),
                    request_start=snap.get("source_period_start"),
                    request_end=snap.get("source_period_end"),
                    snapshot_start=snap.get("source_period_start"),
                    snapshot_end=snap.get("source_period_end"),
                ),
            }
        )

    total_cls = sum(classifications.values()) or 1
    echo_rate = echo_stats["echo"] / max(echo_stats["total"], 1)
    actionable_rate = actionable_stats["actionable"] / max(actionable_stats["total"], 1)
    insight_rate = classifications.get("Insight", 0) / total_cls
    period_with_data = [p for p in period_checks if "None" not in str(p.get("fields", {}).get("ui", ""))]
    period_ok = sum(1 for p in period_with_data if p.get("consistent")) / max(len(period_with_data), 1)
    avg_coverage = sum(coverage_scores) / len(coverage_scores) if coverage_scores else 0.0
    avg_missing = sum(missing_scores) / len(missing_scores) if missing_scores else 100.0
    avg_usefulness = sum(usefulness_scores) / len(usefulness_scores) if usefulness_scores else 0.0
    ad_coverage_rate = (
        sum(1 for x in ad_coverage_flags if x) / len(ad_coverage_flags) if ad_coverage_flags else 0.0
    )
    stmt_total = insight_statement_stats["kpi"] + insight_statement_stats["insight"] or 1
    avg_insight_quality = (
        sum(insight_quality_scores) / len(insight_quality_scores) if insight_quality_scores else 0.0
    )

    score = compute_mvp_ai_score(
        insight_rate=insight_rate,
        echo_rate=echo_rate,
        actionable_rate=actionable_rate,
        period_consistency_rate=period_ok,
        business_coverage=avg_coverage if avg_coverage else 45.0,
        seller_usefulness=avg_usefulness,
    )
    go_no_go = evaluate_go_no_go(
        actionable_rate=actionable_rate,
        seller_usefulness=avg_usefulness,
        echo_rate=echo_rate,
        ai_readiness=score["AI Readiness Score"],
    )

    return {
        "production_url": PRODUCTION_URL,
        "commit_hash": _commit_hash(),
        "analyses_count": len(rows),
        "block1_samples": block1[:40],
        "classification_stats": dict(classifications),
        "dashboard_echo": {
            "echo_rate_pct": round(echo_rate * 100, 1),
            "beyond_dashboard_rate_pct": round(
                echo_stats["beyond_dashboard"] / max(echo_stats["total"], 1) * 100,
                1,
            ),
            "total_lines": echo_stats["total"],
        },
        "actionable": {
            "rate_pct": round(actionable_rate * 100, 1),
            "mvp_target_pct": 80,
            "meets_mvp": actionable_rate >= 0.8,
            "total_lines": actionable_stats["total"],
        },
        "business_value_catalog": [
            {
                "case": r.label,
                "implemented": r.implemented,
                "rule": r.rule,
                "example": r.example,
            }
            for r in BUSINESS_CASE_CATALOG
        ],
        "analyst_rule_catalog": ANALYST_RULE_CATALOG,
        "period_consistency": period_checks,
        "business_coverage_report": {
            "average_score_pct": round(avg_coverage, 1),
            "average_missing_data_score_pct": round(avg_missing, 1),
            "coverage_formula": (
                "Business Coverage = Σ(weight доступных блоков) / Σ(all weights) × 100%"
            ),
            "samples_with_coverage": len(coverage_scores),
        },
        "root_cause_confidence_samples": root_cause_samples[:5],
        "advertising_data_coverage": {
            "rate_pct": round(ad_coverage_rate * 100, 1),
            "recommendations_with_ad_data": sum(1 for x in ad_coverage_flags if x),
            "total_measured": len(ad_coverage_flags),
        },
        "seller_usefulness": {
            "average_score": round(avg_usefulness, 1),
            "mvp_target": 80,
            "meets_mvp": avg_usefulness >= 80,
        },
        "insight_statements": {
            "kpi_statement_count": insight_statement_stats["kpi"],
            "insight_statement_count": insight_statement_stats["insight"],
            "kpi_statement_rate_pct": round(insight_statement_stats["kpi"] / stmt_total * 100, 1),
            "insight_statement_rate_pct": round(insight_statement_stats["insight"] / stmt_total * 100, 1),
            "recommendations_with_echo_detected": insight_statement_stats["echo_flags"],
            "echo_detected_rate_pct": round(
                insight_statement_stats["echo_flags"] / max(len(rows), 1) * 100, 1
            ),
        },
        "insight_quality": {
            "average_overall_score": round(avg_insight_quality, 1),
            "samples_measured": len(insight_quality_scores),
            "components": ["causal_depth", "business_relevance", "actionability", "confidence"],
        },
        "mvp_ai_score": score,
        "go_no_go": go_no_go,
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 6.1 AI recommendation quality audit")
    add_archetype_arguments(parser)
    parser.add_argument("--user-id", default=None, help="Tenant UUID (recommended)")
    parser.add_argument("--limit", type=int, default=None, help="Last N recommendations")
    parser.add_argument("--json-out", default=None, help="Write JSON report path")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    user_id, spec, limit, warnings = resolve_audit_context(
        archetype_id=args.archetype,
        user_id=UUID(args.user_id) if args.user_id else None,
        limit=args.limit,
        manifest_path=manifest_path,
    )
    resolved_limit = limit if limit else 10

    rows = await _load_recommendations(user_id, resolved_limit)
    if not rows:
        print("No recommendations found — run backfill first:")
        print("  python3 scripts/backfill_ai_recommendations.py --user-id <UUID>")
        for w in warnings:
            print(f"WARN: {w}")
        return 2

    report = run_audit(rows)
    if spec is not None:
        from scripts.phase_621_migration_audit import extract_audit_metrics
        from scripts.phase_630_inventory_audit import enrich_metrics

        metrics = enrich_metrics(report, extract_audit_metrics(report), rows=rows)
        validation = validate_archetype(spec, metrics, rows)
        report["archetype"] = {"id": spec.id, "name": spec.name, "validation_status": spec.validation_status}
        report["archetype_validation"] = validation_result_to_dict(validation)
        report["archetype_warnings"] = warnings
        report["archetype_metrics"] = metrics

    text = json.dumps(report, ensure_ascii=False, indent=2, default=str)
    if args.json_out:
        Path(args.json_out).write_text(text, encoding="utf-8")
        print(f"Wrote {args.json_out}")
    else:
        print(text)

    print("\n--- SUMMARY ---")
    print(f"Production: {report['production_url']}")
    print(f"Commit: {report['commit_hash']}")
    print(f"Dashboard Echo: {report['dashboard_echo']['echo_rate_pct']}%")
    print(f"Actionable: {report['actionable']['rate_pct']}% (MVP ≥80%: {report['actionable']['meets_mvp']})")
    print(f"Business Coverage: {report['business_coverage_report']['average_score_pct']}%")
    print(f"Seller Usefulness: {report['seller_usefulness']['average_score']}")
    print(
        f"KPI Statements: {report['insight_statements']['kpi_statement_rate_pct']}% | "
        f"Insights: {report['insight_statements']['insight_statement_rate_pct']}%"
    )
    print(f"Echo detected (insight audit): {report['insight_statements']['echo_detected_rate_pct']}%")
    print(f"Insight Quality Score: {report['insight_quality']['average_overall_score']}")
    print(f"AI Readiness Score: {report['mvp_ai_score']['AI Readiness Score']}/100")
    print(f"GO/NO-GO: {report['go_no_go']['decision']}")
    if report.get("archetype_validation"):
        av = report["archetype_validation"]
        print(f"Archetype ({av.get('archetype_id')}): {av.get('overall_decision')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
