#!/usr/bin/env python3
"""Run archetype validation against AI recommendations (Phase 6.5.2)."""

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
    get_archetype,
    list_archetype_ids,
    load_manifest,
    resolve_audit_context,
    validate_archetype,
    validation_result_to_dict,
)
from scripts.phase_621_migration_audit import extract_audit_metrics
from scripts.phase_630_inventory_audit import enrich_metrics

PILOT_USER = UUID("caefecb3-5789-4878-a9d4-929be573fbcc")


async def audit_archetype(
    archetype_id: str,
    *,
    user_id: UUID | None,
    limit: int,
    manifest_path: Path,
    json_out: Path | None,
) -> dict:
    manifest = load_manifest(manifest_path)
    resolved_uid, spec, resolved_limit, warnings = resolve_audit_context(
        archetype_id=archetype_id,
        user_id=user_id,
        limit=limit,
        manifest_path=manifest_path,
    )
    if spec is None:
        raise KeyError(f"Archetype not found: {archetype_id}")

    payload: dict = {
        "phase": "6.5.2",
        "archetype_id": archetype_id,
        "warnings": warnings,
    }

    if resolved_uid is None:
        payload["overall_decision"] = "SKIP"
        payload["reason"] = "no_user_id"
        payload["archetype"] = {
            "name": spec.name,
            "validation_status": spec.validation_status,
            "dataset_notes": spec.dataset_notes,
        }
        return payload

    rows = await _load_recommendations(resolved_uid, resolved_limit)
    if not rows:
        payload["overall_decision"] = "SKIP"
        payload["reason"] = "no_recommendations"
        payload["user_id"] = str(resolved_uid)
        return payload

    audit = run_audit(rows)
    base_metrics = extract_audit_metrics(audit)
    metrics = enrich_metrics(audit, base_metrics, rows=rows)

    validation = validate_archetype(spec, metrics, rows)
    payload.update(
        {
            "user_id": str(resolved_uid),
            "limit": resolved_limit,
            "analyses_count": len(rows),
            "metrics": metrics,
            "archetype_validation": validation_result_to_dict(validation),
            "overall_decision": validation.overall_decision,
        }
    )

    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return payload


async def audit_all(
    *,
    manifest_path: Path,
    limit: int,
    json_out: Path | None,
) -> dict:
    manifest = load_manifest(manifest_path)
    results: list[dict] = []
    for aid in list_archetype_ids(manifest):
        try:
            result = await audit_archetype(aid, user_id=None, limit=limit, manifest_path=manifest_path, json_out=None)
        except Exception as exc:  # noqa: BLE001 — audit harness must not abort batch
            result = {
                "archetype_id": aid,
                "overall_decision": "SKIP",
                "reason": "audit_error",
                "error": str(exc)[:200],
            }
        results.append(result)

    summary = {
        "phase": "6.5.2",
        "archetypes_tested": len(results),
        "pass": sum(1 for r in results if r.get("overall_decision") == "PASS"),
        "fail": sum(1 for r in results if r.get("overall_decision") == "FAIL"),
        "skip": sum(1 for r in results if r.get("overall_decision") == "SKIP"),
        "results": results,
    }
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return summary


async def main() -> int:
    parser = argparse.ArgumentParser(description="Archetype validation runner (Phase 6.5.2)")
    add_archetype_arguments(parser)
    parser.add_argument("--user-id", default=None, help="Override tenant UUID")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--all", action="store_true", help="Run all archetypes from manifest")
    parser.add_argument(
        "--json-out",
        default="reports/archetype_validation.json",
        help="Write JSON report",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    json_out = Path(args.json_out) if args.json_out else None
    user_id = UUID(args.user_id) if args.user_id else None

    if args.all:
        summary = await audit_all(manifest_path=manifest_path, limit=args.limit or 10, json_out=json_out)
        print("\n=== Archetype Validation — All P0 ===")
        print(f"PASS: {summary['pass']}  FAIL: {summary['fail']}  SKIP: {summary['skip']}")
        for row in summary["results"]:
            print(f"  {row.get('archetype_id', '?'):<25} {row.get('overall_decision', '?')}")
        if json_out:
            print(f"\nReport: {json_out}")
        return 0 if summary["fail"] == 0 else 1

    archetype_id = args.archetype or "high_inventory_seller"
    result = await audit_archetype(
        archetype_id,
        user_id=user_id,
        limit=args.limit or 10,
        manifest_path=manifest_path,
        json_out=json_out,
    )

    print(f"\n=== Archetype Validation — {archetype_id} ===")
    if result.get("warnings"):
        for w in result["warnings"]:
            print(f"WARN: {w}")
    av = result.get("archetype_validation") or {}
    print(f"Decision: {result.get('overall_decision', '?')}")
    if av.get("metric_results"):
        print(f"\n{'Metric':<28} {'Value':>8} {'Min':>8} {'Target':>8} {'Status':>8}")
        for mr in av["metric_results"]:
            print(
                f"{mr['metric']:<28} {mr['value']:>8.1f} {mr['minimum']:>8.1f} "
                f"{mr['target']:>8.1f} {mr['status']:>8}"
            )
    if json_out:
        print(f"\nReport: {json_out}")
    return 0 if result.get("overall_decision") in ("PASS", "SKIP") else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
