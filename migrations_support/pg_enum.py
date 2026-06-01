"""Idempotent PostgreSQL ENUM creation for Alembic migrations."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


def ensure_pg_enum(type_name: str, labels: tuple[str, ...]) -> None:
    """Create ENUM type if missing; no-op when it already exists."""
    labels_sql = ", ".join(f"'{label}'" for label in labels)
    op.execute(
        sa.text(
            f"""
            DO $do$
            BEGIN
                CREATE TYPE {type_name} AS ENUM ({labels_sql});
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END
            $do$;
            """
        )
    )
