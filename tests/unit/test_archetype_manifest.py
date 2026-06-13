"""Unit tests for seller archetype manifest and validation helpers."""

from __future__ import annotations

from pathlib import Path

from scripts.archetype_validation import (
    METRIC_KEYS,
    MetricBand,
    evaluate_metric_band,
    get_archetype,
    list_archetype_ids,
    load_manifest,
    validate_manifest_schema,
)

MANIFEST = Path(__file__).resolve().parents[1] / "fixtures" / "seller_archetypes" / "manifest.json"


def test_manifest_file_exists() -> None:
    assert MANIFEST.is_file()


def test_manifest_schema_valid() -> None:
    errors = validate_manifest_schema(load_manifest(MANIFEST))
    assert errors == []


def test_manifest_has_five_p0_archetypes() -> None:
    ids = list_archetype_ids(load_manifest(MANIFEST))
    assert len(ids) >= 5
    for expected in (
        "small_seller",
        "seasonal_seller",
        "unprofitable_seller",
        "no_ads_seller",
        "high_inventory_seller",
    ):
        assert expected in ids


def test_each_archetype_has_metric_bands() -> None:
    for aid in list_archetype_ids(load_manifest(MANIFEST)):
        spec = get_archetype(aid, load_manifest(MANIFEST))
        for key in METRIC_KEYS:
            assert key in spec.metric_bands, f"{aid} missing band {key}"


def test_high_inventory_seller_maps_to_pilot() -> None:
    spec = get_archetype("high_inventory_seller", load_manifest(MANIFEST))
    assert spec.validation_status == "validated"
    assert spec.user_id is not None
    assert str(spec.user_id) == "caefecb3-5789-4878-a9d4-929be573fbcc"


def test_pending_archetypes_have_no_user_id() -> None:
    for aid in ("small_seller", "seasonal_seller", "unprofitable_seller", "no_ads_seller"):
        spec = get_archetype(aid, load_manifest(MANIFEST))
        assert spec.user_id is None
        assert spec.validation_status == "pending_dataset"


def test_metric_band_pass_and_fail() -> None:
    band = MetricBand(minimum=74.0, target=80.0, stretch=88.0)
    assert evaluate_metric_band(80.3, band).status == "TARGET"
    assert evaluate_metric_band(70.0, band).status == "FAIL"
    assert evaluate_metric_band(90.0, band).status == "STRETCH"


def test_dashboard_echo_band_inverted() -> None:
    band = MetricBand(minimum=0.0, target=0.0, stretch=0.0, maximum=0.0)
    assert evaluate_metric_band(0.0, band, higher_is_better=False).status == "STRETCH"
    assert evaluate_metric_band(5.0, band, higher_is_better=False).status == "FAIL"
