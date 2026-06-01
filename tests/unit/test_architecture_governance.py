"""Unit tests for architecture fitness functions."""

from __future__ import annotations

from scripts.architecture_governance_check import (
    check_governed_module_tests,
    check_layer_imports,
    check_required_docs,
)


def test_required_architecture_docs_present() -> None:
    assert check_required_docs() == []


def test_layer_import_rules_no_errors() -> None:
    errors, _warnings = check_layer_imports()
    assert errors == []


def test_governed_operations_tests_exist() -> None:
    warnings = check_governed_module_tests()
    assert not any("app/operations/" in w for w in warnings)
