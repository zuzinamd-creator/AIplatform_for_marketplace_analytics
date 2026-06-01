from collections.abc import Generator

import pytest
from app.domain.inventory.errors import UnsupportedSemanticsVersionError
from app.domain.semantics.governance_policy import (
    SemanticsLifecycleRecord,
    SemanticsLifecycleStatus,
    clear_lifecycle_cache,
    set_lifecycle_cache,
)
from app.parsers.wb.semantics_registry import build_strategy_cache


@pytest.fixture(autouse=True)
def _reset_lifecycle_cache() -> Generator[None, None, None]:
    clear_lifecycle_cache()
    yield
    clear_lifecycle_cache()


def test_deprecated_replay_allowed() -> None:
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
    cache = build_strategy_cache({"1.0"})
    assert cache["1.0"].version == "1.0"


def test_disabled_replay_fails() -> None:
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
        build_strategy_cache({"1.0"})
