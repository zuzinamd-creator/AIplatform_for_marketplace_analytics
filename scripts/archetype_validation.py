"""Archetype Validation Framework — load manifest, evaluate metric bands and insight rules."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "tests" / "fixtures" / "seller_archetypes" / "manifest.json"

METRIC_KEYS = (
    "seller_usefulness",
    "ai_readiness",
    "actionable_rate_pct",
    "inventory_insight_rate_pct",
    "dashboard_echo_pct",
)


@dataclass(frozen=True)
class MetricBand:
    minimum: float
    target: float
    stretch: float
    maximum: float | None = None


@dataclass(frozen=True)
class InsightExpectations:
    finding_ids: tuple[str, ...]
    primary_domains: tuple[str, ...]
    text_patterns: tuple[str, ...]
    rules: tuple[str, ...] = ()


@dataclass(frozen=True)
class ArchetypeSpec:
    id: str
    name: str
    priority: str
    validation_status: str
    user_id: UUID | None
    reports_min: int
    business_profile: dict[str, Any]
    kpi_expectations: dict[str, Any]
    metric_bands: dict[str, MetricBand]
    expected_insights: InsightExpectations
    optional_insights: InsightExpectations
    forbidden_insights: InsightExpectations
    dataset_notes: str = ""


@dataclass
class MetricBandResult:
    metric: str
    value: float
    minimum: float
    target: float
    stretch: float
    maximum: float | None
    status: str  # FAIL | PASS | TARGET | STRETCH


@dataclass
class ArchetypeValidationResult:
    archetype_id: str
    archetype_name: str
    validation_status: str
    user_id: str | None
    metrics: dict[str, float]
    metric_results: list[MetricBandResult] = field(default_factory=list)
    metric_decision: str = "SKIP"
    insight_hits: dict[str, list[str]] = field(default_factory=dict)
    insight_decision: str = "SKIP"
    overall_decision: str = "SKIP"
    notes: list[str] = field(default_factory=list)


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    manifest_path = path or DEFAULT_MANIFEST
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Archetype manifest not found: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def list_archetype_ids(manifest: dict[str, Any] | None = None) -> list[str]:
    data = manifest or load_manifest()
    return [a["id"] for a in data.get("archetypes", [])]


def _parse_insight_block(block: dict[str, Any] | None) -> InsightExpectations:
    block = block or {}
    return InsightExpectations(
        finding_ids=tuple(block.get("finding_ids") or []),
        primary_domains=tuple(block.get("primary_domains") or []),
        text_patterns=tuple(block.get("text_patterns") or []),
        rules=tuple(block.get("rules") or []),
    )


def _parse_metric_bands(raw: dict[str, Any]) -> dict[str, MetricBand]:
    bands: dict[str, MetricBand] = {}
    for key, spec in (raw or {}).items():
        bands[key] = MetricBand(
            minimum=float(spec["minimum"]),
            target=float(spec["target"]),
            stretch=float(spec["stretch"]),
            maximum=float(spec["maximum"]) if spec.get("maximum") is not None else None,
        )
    return bands


def get_archetype(archetype_id: str, manifest: dict[str, Any] | None = None) -> ArchetypeSpec:
    data = manifest or load_manifest()
    for raw in data.get("archetypes", []):
        if raw["id"] == archetype_id:
            uid = raw.get("user_id")
            return ArchetypeSpec(
                id=raw["id"],
                name=raw["name"],
                priority=raw.get("priority", "P0"),
                validation_status=raw.get("validation_status", "pending_dataset"),
                user_id=UUID(uid) if uid else None,
                reports_min=int(raw.get("reports_min") or 2),
                business_profile=dict(raw.get("business_profile") or {}),
                kpi_expectations=dict(raw.get("kpi_expectations") or {}),
                metric_bands=_parse_metric_bands(raw.get("metric_bands") or {}),
                expected_insights=_parse_insight_block(raw.get("expected_insights")),
                optional_insights=_parse_insight_block(raw.get("optional_insights")),
                forbidden_insights=_parse_insight_block(raw.get("forbidden_insights")),
                dataset_notes=str(raw.get("dataset_notes") or ""),
            )
    known = ", ".join(list_archetype_ids(data))
    raise KeyError(f"Unknown archetype '{archetype_id}'. Known: {known}")


def resolve_audit_context(
    *,
    archetype_id: str | None = None,
    user_id: UUID | None = None,
    limit: int | None = None,
    manifest_path: Path | None = None,
) -> tuple[UUID | None, ArchetypeSpec | None, int, list[str]]:
    """Resolve user_id and limit from archetype manifest. Returns (user_id, spec, limit, warnings)."""
    warnings: list[str] = []
    spec: ArchetypeSpec | None = None
    resolved_limit = limit if limit is not None else 10

    if not archetype_id:
        return user_id, None, resolved_limit, warnings

    spec = get_archetype(archetype_id, load_manifest(manifest_path))
    if user_id is None:
        user_id = spec.user_id
    if user_id is None:
        warnings.append(
            f"Archetype '{archetype_id}' has no user_id — assign tenant or load dataset (status: {spec.validation_status})"
        )
    if limit is None:
        resolved_limit = max(spec.reports_min, 4)
    return user_id, spec, resolved_limit, warnings


def evaluate_metric_band(value: float, band: MetricBand, *, higher_is_better: bool = True) -> MetricBandResult:
    if not higher_is_better:
        if band.maximum is not None and value > band.maximum:
            status = "FAIL"
        elif value <= band.stretch:
            status = "STRETCH"
        elif value <= band.target:
            status = "TARGET"
        elif value <= band.minimum:
            status = "PASS"
        else:
            status = "FAIL"
        return MetricBandResult(
            metric="",
            value=value,
            minimum=band.minimum,
            target=band.target,
            stretch=band.stretch,
            maximum=band.maximum,
            status=status,
        )

    if value < band.minimum:
        status = "FAIL"
    elif value >= band.stretch:
        status = "STRETCH"
    elif value >= band.target:
        status = "TARGET"
    else:
        status = "PASS"
    return MetricBandResult(
        metric="",
        value=value,
        minimum=band.minimum,
        target=band.target,
        stretch=band.stretch,
        maximum=band.maximum,
        status=status,
    )


def evaluate_metric_bands(metrics: dict[str, float], spec: ArchetypeSpec) -> list[MetricBandResult]:
    results: list[MetricBandResult] = []
    for key in METRIC_KEYS:
        band = spec.metric_bands.get(key)
        if band is None:
            continue
        value = float(metrics.get(key, 0.0))
        higher_is_better = key != "dashboard_echo_pct"
        row = evaluate_metric_band(value, band, higher_is_better=higher_is_better)
        results.append(
            MetricBandResult(
                metric=key,
                value=row.value,
                minimum=row.minimum,
                target=row.target,
                stretch=row.stretch,
                maximum=row.maximum,
                status=row.status,
            )
        )
    return results


def _collect_finding_ids_from_rows(rows: list[Any]) -> set[str]:
    finding_ids: set[str] = set()
    for rec in rows:
        plan = rec.action_plan or {}
        su = plan.get("seller_usefulness") or plan
        engine = su.get("insight_engine") or plan.get("insight_engine") or {}
        for item in engine.get("structured_insights") or []:
            if isinstance(item, dict):
                fid = item.get("finding_id") or item.get("insight_id") or ""
                if fid:
                    finding_ids.add(str(fid).split(":")[-1])
        rt = rec.reasoning_trace or {}
        for out in (rt.get("multi_layer") or {}).get("domain_outputs") or []:
            for f in out.get("findings") or []:
                fid = f.get("finding_id")
                if fid:
                    finding_ids.add(str(fid))
    return finding_ids


def _collect_primary_domain(rows: list[Any]) -> str | None:
    for rec in rows:
        plan = rec.action_plan or {}
        su = plan.get("seller_usefulness") or plan
        engine = su.get("insight_engine") or plan.get("insight_engine") or {}
        primary = engine.get("primary_insight") or {}
        if isinstance(primary, dict):
            fid = str(primary.get("finding_id") or primary.get("insight_id") or "")
            text = str(primary.get("what_happened") or rec.title or "").lower()
            return _domain_from_finding(fid, text)
    return None


def _domain_from_finding(fid: str, text: str) -> str:
    fid_l = fid.lower()
    if fid_l.startswith("inventory_") or any(m in text for m in ("остатк", "мёртв", "заморож")):
        return "inventory"
    if fid_l.startswith("revenue_") or fid_l == "sales_top_sku" or "выручк" in text:
        return "revenue"
    if "profit" in fid_l or "убыт" in text or "маржа" in text:
        return "profit" if "убыт" in text else "margin"
    if fid_l.startswith("logistics_"):
        return "logistics"
    if fid_l.startswith("returns_"):
        return "returns"
    if fid_l.startswith("concentration_"):
        return "concentration"
    if fid_l.startswith("ads_") or "реклам" in text:
        return "ads"
    return "other"


def _text_blob(rows: list[Any]) -> str:
    parts: list[str] = []
    for rec in rows:
        plan = rec.action_plan or {}
        parts.extend([rec.title or "", rec.summary or "", str(plan.get("recommended_action") or "")])
    return " ".join(parts).lower()


def evaluate_insight_expectations(rows: list[Any], spec: ArchetypeSpec) -> tuple[dict[str, list[str]], str, list[str]]:
    """Return (hits, decision, notes). decision: PASS | FAIL | SKIP."""
    notes: list[str] = []
    if not rows:
        return {}, "SKIP", ["No recommendations to evaluate insight expectations"]

    finding_ids = _collect_finding_ids_from_rows(rows)
    primary_domain = _collect_primary_domain(rows)
    text = _text_blob(rows)

    hits: dict[str, list[str]] = {
        "expected_finding_ids": [f for f in spec.expected_insights.finding_ids if f in finding_ids],
        "optional_finding_ids": [f for f in spec.optional_insights.finding_ids if f in finding_ids],
        "forbidden_finding_ids_hit": [f for f in spec.forbidden_insights.finding_ids if f in finding_ids],
        "forbidden_pattern_hits": [p for p in spec.forbidden_insights.text_patterns if p.lower() in text],
        "expected_pattern_hits": [p for p in spec.expected_insights.text_patterns if p.lower() in text],
        "primary_domain": [primary_domain] if primary_domain else [],
    }

    fail = False
    if spec.expected_insights.finding_ids and not hits["expected_finding_ids"] and not hits["expected_pattern_hits"]:
        notes.append("No expected finding_ids or text patterns matched")
        fail = True

    if hits["forbidden_finding_ids_hit"]:
        notes.append(f"Forbidden finding_ids present: {hits['forbidden_finding_ids_hit']}")
        fail = True

    forbidden_domains = spec.forbidden_insights.primary_domains
    if primary_domain and primary_domain in forbidden_domains:
        notes.append(f"Forbidden primary domain: {primary_domain}")
        fail = True

    if hits["forbidden_pattern_hits"] and primary_domain in ("ads", "inventory") and spec.id == "no_ads_seller":
        notes.append(f"Forbidden text patterns in output: {hits['forbidden_pattern_hits']}")
        fail = True
    elif hits["forbidden_pattern_hits"] and spec.id == "no_ads_seller":
        notes.append(f"Forbidden ad patterns detected: {hits['forbidden_pattern_hits']}")
        fail = True

    if spec.id == "high_inventory_seller" and primary_domain == "ads":
        notes.append("Ads must not be primary for high inventory seller when inventory risk present")
        fail = True

    if not fail and (hits["expected_finding_ids"] or hits["expected_pattern_hits"] or spec.validation_status != "validated"):
        return hits, "PASS" if not fail else "FAIL", notes

    return hits, "FAIL" if fail else "PASS", notes


def validate_archetype(
    spec: ArchetypeSpec,
    metrics: dict[str, float],
    rows: list[Any] | None = None,
) -> ArchetypeValidationResult:
    result = ArchetypeValidationResult(
        archetype_id=spec.id,
        archetype_name=spec.name,
        validation_status=spec.validation_status,
        user_id=str(spec.user_id) if spec.user_id else None,
        metrics=dict(metrics),
    )

    if spec.validation_status == "pending_dataset" and not rows:
        result.notes.append("Dataset pending — metric/insight validation skipped")
        result.overall_decision = "SKIP"
        return result

    band_results = evaluate_metric_bands(metrics, spec)
    result.metric_results = band_results
    if band_results:
        result.metric_decision = "FAIL" if any(r.status == "FAIL" for r in band_results) else "PASS"
    else:
        result.metric_decision = "SKIP"

    if rows:
        hits, insight_decision, insight_notes = evaluate_insight_expectations(rows, spec)
        result.insight_hits = hits
        result.insight_decision = insight_decision
        result.notes.extend(insight_notes)
    else:
        result.insight_decision = "SKIP"

    decisions = {result.metric_decision, result.insight_decision} - {"SKIP"}
    if not decisions:
        result.overall_decision = "SKIP"
    elif "FAIL" in decisions:
        result.overall_decision = "FAIL"
    else:
        result.overall_decision = "PASS"

    return result


def validation_result_to_dict(result: ArchetypeValidationResult) -> dict[str, Any]:
    return {
        "archetype_id": result.archetype_id,
        "archetype_name": result.archetype_name,
        "validation_status": result.validation_status,
        "user_id": result.user_id,
        "metrics": result.metrics,
        "metric_results": [
            {
                "metric": r.metric,
                "value": r.value,
                "minimum": r.minimum,
                "target": r.target,
                "stretch": r.stretch,
                "maximum": r.maximum,
                "status": r.status,
            }
            for r in result.metric_results
        ],
        "metric_decision": result.metric_decision,
        "insight_hits": result.insight_hits,
        "insight_decision": result.insight_decision,
        "overall_decision": result.overall_decision,
        "notes": result.notes,
    }


def add_archetype_arguments(parser: Any) -> None:
    parser.add_argument(
        "--archetype",
        default=None,
        help="Seller archetype id from tests/fixtures/seller_archetypes/manifest.json",
    )
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST),
        help="Path to archetype manifest JSON",
    )


def validate_manifest_schema(manifest: dict[str, Any] | None = None) -> list[str]:
    """Return list of schema errors (empty = valid)."""
    errors: list[str] = []
    data = manifest or load_manifest()
    if data.get("schema") != "seller_archetype_v1":
        errors.append("schema must be seller_archetype_v1")
    archetypes = data.get("archetypes")
    if not isinstance(archetypes, list) or len(archetypes) < 5:
        errors.append("archetypes must be a list with at least 5 entries")
        return errors

    ids: set[str] = set()
    for idx, arch in enumerate(archetypes):
        prefix = f"archetypes[{idx}]"
        aid = arch.get("id")
        if not aid:
            errors.append(f"{prefix}: missing id")
            continue
        if aid in ids:
            errors.append(f"{prefix}: duplicate id '{aid}'")
        ids.add(aid)
        for block_name in ("expected_insights", "optional_insights", "forbidden_insights"):
            block = arch.get(block_name)
            if block is None:
                errors.append(f"{prefix}: missing {block_name}")
        bands = arch.get("metric_bands") or {}
        for mk in METRIC_KEYS:
            if mk not in bands:
                errors.append(f"{prefix}: metric_bands missing '{mk}'")
            else:
                for tier in ("minimum", "target", "stretch"):
                    if tier not in bands[mk]:
                        errors.append(f"{prefix}: metric_bands.{mk} missing '{tier}'")
    return errors
