from collections.abc import Generator

import pytest
from app.domain.inventory.errors import UnsupportedSemanticsVersionError
from app.domain.semantics.governance_policy import (
    SemanticsLifecycleRecord,
    SemanticsLifecycleStatus,
    assert_ingest_allowed,
    assert_rebuild_allowed,
    clear_lifecycle_cache,
    set_lifecycle_cache,
)
from app.parsers.wb.semantics_registry import SEMANTICS_REGISTRY


@pytest.fixture(autouse=True)
def _reset_lifecycle_cache() -> Generator[None, None, None]:
    clear_lifecycle_cache()
    yield
    clear_lifecycle_cache()


def test_active_ingest_and_rebuild_allowed() -> None:
    assert_ingest_allowed("1.0")
    assert_rebuild_allowed("1.0")


def test_deprecated_blocks_ingest_allows_rebuild() -> None:
    set_lifecycle_cache(
        {
            "1.0": SemanticsLifecycleRecord(
                version="1.0",
                status=SemanticsLifecycleStatus.DEPRECATED,
                supported_for_rebuild=True,
                supported_for_ingest=False,
            ),
        }
    )
    with pytest.raises(UnsupportedSemanticsVersionError):
        assert_ingest_allowed("1.0")
    assert_rebuild_allowed("1.0")


def test_disabled_blocks_ingest_and_rebuild() -> None:
    set_lifecycle_cache(
        {
            "1.0": SemanticsLifecycleRecord(
                version="1.0",
                status=SemanticsLifecycleStatus.DISABLED,
                supported_for_rebuild=False,
                supported_for_ingest=False,
            ),
        }
    )
    with pytest.raises(UnsupportedSemanticsVersionError):
        assert_ingest_allowed("1.0")
    with pytest.raises(UnsupportedSemanticsVersionError):
        assert_rebuild_allowed("1.0")


def test_unknown_version_raises() -> None:
    with pytest.raises(UnsupportedSemanticsVersionError):
        assert_ingest_allowed("99.0")


def test_rebuild_requires_registry_strategy() -> None:
    set_lifecycle_cache(
        {
            "9.9": SemanticsLifecycleRecord(
                version="9.9",
                status=SemanticsLifecycleStatus.ACTIVE,
                supported_for_rebuild=True,
                supported_for_ingest=True,
            ),
        }
    )
    assert "9.9" not in SEMANTICS_REGISTRY
    with pytest.raises(UnsupportedSemanticsVersionError):
        assert_rebuild_allowed("9.9")
