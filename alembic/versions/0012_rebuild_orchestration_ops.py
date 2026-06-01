"""rebuild orchestration metadata on snapshot_rebuild_requirements

Revision ID: 0012_rebuild_orchestration
Revises: 0011_operability_semantics
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from migrations_support.pg_enum import ensure_pg_enum

revision: str = "0012_rebuild_orchestration"
down_revision: str | Sequence[str] | None = "0011_operability_semantics"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUS_LABELS = ("pending", "queued", "running", "succeeded", "failed", "deferred")
MODE_LABELS = ("incremental", "full")


def upgrade() -> None:
    ensure_pg_enum("rebuild_orchestration_status_enum", STATUS_LABELS)
    ensure_pg_enum("rebuild_mode_enum", MODE_LABELS)
    status_enum = sa.Enum(*STATUS_LABELS, name="rebuild_orchestration_status_enum", create_type=False)
    mode_enum = sa.Enum(*MODE_LABELS, name="rebuild_mode_enum", create_type=False)

    op.add_column(
        "snapshot_rebuild_requirements",
        sa.Column(
            "orchestration_status",
            status_enum,
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "snapshot_rebuild_requirements",
        sa.Column("rebuild_mode", mode_enum, nullable=False, server_default="incremental"),
    )
    op.add_column(
        "snapshot_rebuild_requirements",
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
    )
    op.add_column(
        "snapshot_rebuild_requirements",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "snapshot_rebuild_requirements",
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
    )
    op.add_column(
        "snapshot_rebuild_requirements",
        sa.Column("last_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "snapshot_rebuild_requirements",
        sa.Column("last_attempted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "snapshot_rebuild_requirements",
        sa.Column("next_eligible_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "snapshot_rebuild_requirements",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "snapshot_rebuild_requirements",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_snapshot_rebuild_req_status_priority",
        "snapshot_rebuild_requirements",
        ["orchestration_status", "priority", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_snapshot_rebuild_req_status_priority", table_name="snapshot_rebuild_requirements")
    for col in (
        "completed_at",
        "started_at",
        "next_eligible_at",
        "last_attempted_at",
        "last_error",
        "max_attempts",
        "attempt_count",
        "priority",
        "rebuild_mode",
        "orchestration_status",
    ):
        op.drop_column("snapshot_rebuild_requirements", col)
    op.execute(sa.text("DROP TYPE IF EXISTS rebuild_mode_enum"))
    op.execute(sa.text("DROP TYPE IF EXISTS rebuild_orchestration_status_enum"))
