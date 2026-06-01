"""
PRODUCT-VALIDATION: Real seller workflow simulation harness.

Exercises existing APIs across daily, weekly, incident, and growth workflows.
Does NOT mutate backend semantics — read-only validation + optional upload/AI runs.

Usage:
  python scripts/product_validation_simulation.py --workflow daily --report-file path.csv
  python scripts/product_validation_simulation.py --workflow weekly
  python scripts/product_validation_simulation.py --workflow incident
  python scripts/product_validation_simulation.py --workflow growth
  python scripts/product_validation_simulation.py --workflow all --run-ai
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests

# Allow importing shared helpers from sibling script.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ux2_real_data_validation import auth_headers, login, register, run_intelligence, upload_report


def _get(base_url: str, api_prefix: str, token: str, path: str, params: dict | None = None) -> dict:
    url = f"{base_url}{api_prefix}{path}"
    r = requests.get(url, headers=auth_headers(token), params=params or {}, timeout=60)
    r.raise_for_status()
    return r.json()


def _emit(event: str, **kwargs) -> None:
    print(json.dumps({"event": event, **kwargs}, ensure_ascii=False))


def simulate_daily(
    base_url: str,
    api_prefix: str,
    token: str,
    *,
    report_file: Path | None,
    marketplace: str,
    report_type: str,
    run_ai: bool,
) -> str | None:
    _emit("workflow_start", workflow="daily")
    report_id: str | None = None
    if report_file:
        uploaded = upload_report(base_url, api_prefix, token, marketplace, report_type, report_file)
        report_id = uploaded["report"]["id"]
        _emit("upload_complete", report_id=report_id)

    end = date.today()
    start = end - timedelta(days=13)
    summary = _get(
        base_url,
        api_prefix,
        token,
        "/analytics/kpis/summary",
        {"marketplace": marketplace, "start": start.isoformat(), "end": end.isoformat()},
    )
    _emit(
        "kpi_summary",
        total_revenue=summary.get("kpis", {}).get("total_revenue"),
        stale=summary.get("freshness", {}).get("stale_data_warning"),
    )

    anomalies = _get(base_url, api_prefix, token, "/ops/anomalies", {"skip": 0, "limit": 5})
    _emit("anomalies_checked", count=len(anomalies.get("items", [])))

    recs = _get(base_url, api_prefix, token, "/ai/recommendations", {"skip": 0, "limit": 5})
    _emit("recommendations_checked", count=len(recs.get("items", [])))

    if run_ai:
        res = run_intelligence(base_url, api_prefix, token, report_id)
        _emit("ai_run_complete", recommendation_id=res.get("recommendation_id"))

    _emit("workflow_complete", workflow="daily")
    return report_id


def simulate_weekly(base_url: str, api_prefix: str, token: str, *, marketplace: str) -> None:
    _emit("workflow_start", workflow="weekly")
    end = date.today()
    start = end - timedelta(days=13)
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=13)

    compare = _get(
        base_url,
        api_prefix,
        token,
        "/analytics/kpis/period-compare",
        {
            "marketplace": marketplace,
            "a_start": start.isoformat(),
            "a_end": end.isoformat(),
            "b_start": prev_start.isoformat(),
            "b_end": prev_end.isoformat(),
        },
    )
    _emit(
        "period_compare",
        delta_revenue=compare.get("delta_revenue"),
        delta_profit=compare.get("delta_profit"),
    )

    top = _get(
        base_url,
        api_prefix,
        token,
        "/analytics/kpis/top-skus",
        {
            "marketplace": marketplace,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "limit": 10,
            "sort": "profit",
        },
    )
    _emit("profit_skus_scan", count=len(top.get("items", [])))

    abc = _get(
        base_url,
        api_prefix,
        token,
        "/analytics/kpis/abc",
        {"marketplace": marketplace, "start": start.isoformat(), "end": end.isoformat()},
    )
    _emit("abc_analysis", buckets=[b.get("bucket") for b in abc.get("buckets", [])])

    risk = _get(
        base_url,
        api_prefix,
        token,
        "/analytics/kpis/inventory-risk",
        {"snapshot_date": end.isoformat(), "semantics_version": "1.0"},
    )
    _emit("warehouse_risk", discrepancy_cost=risk.get("discrepancy_cost_total"))

    _emit("workflow_complete", workflow="weekly")


def simulate_incident(base_url: str, api_prefix: str, token: str, *, report_id: str | None) -> None:
    _emit("workflow_start", workflow="incident")

    runtime = _get(base_url, api_prefix, token, "/ops/runtime/summary")
    _emit("runtime_summary", rebuild=runtime.get("rebuild"), queue=runtime.get("queue"))

    rebuilds = _get(base_url, api_prefix, token, "/ops/rebuilds", {"skip": 0, "limit": 5})
    _emit("rebuilds_checked", count=len(rebuilds.get("items", [])))

    if report_id:
        rep = _get(base_url, api_prefix, token, f"/reports/{report_id}")
        _emit("broken_report_check", status=rep.get("status"), job=rep.get("job"))

    end = date.today()
    summary = _get(
        base_url,
        api_prefix,
        token,
        "/analytics/kpis/summary",
        {
            "marketplace": "wildberries",
            "start": (end - timedelta(days=13)).isoformat(),
            "end": end.isoformat(),
        },
    )
    _emit("stale_analytics_check", stale=summary.get("freshness", {}).get("stale_data_warning"))

    recs = _get(base_url, api_prefix, token, "/ai/recommendations", {"skip": 0, "limit": 3})
    if recs.get("items"):
        rec_id = recs["items"][0]["id"]
        explain = _get(base_url, api_prefix, token, f"/ai/recommendations/{rec_id}/explainability")
        graph = explain.get("evidence_graph") or {}
        _emit(
            "suspicious_recommendation_review",
            recommendation_id=rec_id,
            evidence_nodes=len(graph.get("nodes", [])),
        )

    drift = _get(base_url, api_prefix, token, "/ops/drift-checks", {"skip": 0, "limit": 5})
    _emit("inventory_anomaly_check", drift_count=len(drift.get("items", [])))

    _emit("workflow_complete", workflow="incident")


def simulate_growth(base_url: str, api_prefix: str, token: str, *, marketplace: str) -> None:
    _emit("workflow_start", workflow="growth")
    end = date.today()
    start = end - timedelta(days=29)

    top_rev = _get(
        base_url,
        api_prefix,
        token,
        "/analytics/kpis/top-skus",
        {
            "marketplace": marketplace,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "limit": 5,
            "sort": "revenue",
        },
    )
    _emit("growth_opportunities", top_skus=[i.get("sku") for i in top_rev.get("items", [])])

    abc = _get(
        base_url,
        api_prefix,
        token,
        "/analytics/kpis/abc",
        {"marketplace": marketplace, "start": start.isoformat(), "end": end.isoformat()},
    )
    a_bucket = next((b for b in abc.get("buckets", []) if b.get("bucket") == "A"), {})
    _emit("margin_focus", a_sku_count=a_bucket.get("sku_count"), a_revenue_pct=a_bucket.get("revenue_pct"))

    risk = _get(
        base_url,
        api_prefix,
        token,
        "/analytics/kpis/inventory-risk",
        {"snapshot_date": end.isoformat()},
    )
    _emit("stock_optimization_signal", warehouses_with_discrepancies=risk.get("warehouses_with_discrepancies"))

    stats = _get(base_url, api_prefix, token, "/ai/recommendations/stats")
    _emit("ai_feedback_stats", helpful_rate=stats.get("helpful_rate"), ignored_7d=stats.get("ignored_7d"))

    _emit("workflow_complete", workflow="growth")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8080")
    ap.add_argument("--api-prefix", default="/api/v1")
    ap.add_argument("--email", default="validation_seller@example.com")
    ap.add_argument("--password", default="validation_password_123")
    ap.add_argument("--marketplace", default="wildberries")
    ap.add_argument("--report-type", default="sales")
    ap.add_argument("--report-file", default=None)
    ap.add_argument("--workflow", choices=["daily", "weekly", "incident", "growth", "all"], default="all")
    ap.add_argument("--run-ai", action="store_true")
    args = ap.parse_args()

    report_file = Path(args.report_file) if args.report_file else None
    if report_file and not report_file.exists():
        raise SystemExit(f"report file not found: {report_file}")

    register(args.base_url, args.api_prefix, args.email, args.password)
    token = login(args.base_url, args.api_prefix, args.email, args.password)

    report_id: str | None = None
    t0 = time.time()
    workflows = [args.workflow] if args.workflow != "all" else ["daily", "weekly", "incident", "growth"]

    for wf in workflows:
        if wf == "daily":
            report_id = simulate_daily(
                args.base_url,
                args.api_prefix,
                token,
                report_file=report_file,
                marketplace=args.marketplace,
                report_type=args.report_type,
                run_ai=args.run_ai,
            )
        elif wf == "weekly":
            simulate_weekly(args.base_url, args.api_prefix, token, marketplace=args.marketplace)
        elif wf == "incident":
            simulate_incident(args.base_url, args.api_prefix, token, report_id=report_id)
        elif wf == "growth":
            simulate_growth(args.base_url, args.api_prefix, token, marketplace=args.marketplace)

    _emit("simulation_complete", elapsed_s=round(time.time() - t0, 3), workflows=workflows)


if __name__ == "__main__":
    main()
