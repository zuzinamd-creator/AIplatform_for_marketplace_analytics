"""Backward-compatible re-export; prefer migrations_support.pg_enum in new revisions."""

from migrations_support.pg_enum import ensure_pg_enum

__all__ = ["ensure_pg_enum"]
