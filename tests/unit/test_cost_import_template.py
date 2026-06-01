"""Cost import template file and path resolution."""

from __future__ import annotations

from app.core.template_paths import cost_import_template_path


def test_cost_import_template_exists() -> None:
    path = cost_import_template_path()
    assert path.is_file()
    assert path.suffix == ".xlsx"
    assert path.stat().st_size > 0
