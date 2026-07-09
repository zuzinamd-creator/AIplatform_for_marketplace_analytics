"""registration_invites — invite-only seller onboarding (Phase 9.3A).

Revision ID: 0035_registration_invites
Revises: 0034_user_role_platform_admin
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0035_registration_invites"
down_revision: str | Sequence[str] | None = "0034_user_role_platform_admin"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _lockdown_table(table_name: str) -> None:
    op.execute(sa.text(f"REVOKE ALL ON TABLE public.{table_name} FROM anon, authenticated"))
    op.execute(sa.text(f"ALTER TABLE public.{table_name} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE public.{table_name} FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"DROP POLICY IF EXISTS {table_name}_backend_only ON public.{table_name}"))
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {table_name}_backend_only
            ON public.{table_name}
            FOR ALL
            TO marketplace_app
            USING (true)
            WITH CHECK (true)
            """
        )
    )


def upgrade() -> None:
    op.create_table(
        "registration_invites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'seller'"),
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("invited_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["invited_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("role IN ('seller', 'platform_admin')", name="ck_registration_invites_role_valid"),
        sa.CheckConstraint(
            "NOT (used_at IS NOT NULL AND revoked_at IS NOT NULL)",
            name="ck_registration_invites_used_revoked_exclusive",
        ),
    )
    op.create_index("ix_registration_invites_email", "registration_invites", ["email"])
    op.create_index("ix_registration_invites_token_hash", "registration_invites", ["token_hash"], unique=True)
    op.create_index("ix_registration_invites_invited_by_id", "registration_invites", ["invited_by_id"])
    op.create_index("ix_registration_invites_expires_at", "registration_invites", ["expires_at"])
    op.execute(
        """
        CREATE UNIQUE INDEX uq_registration_invites_active_email
        ON registration_invites (lower(email))
        WHERE used_at IS NULL AND revoked_at IS NULL
        """
    )
    _lockdown_table("registration_invites")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS registration_invites_backend_only ON registration_invites")
    op.execute("ALTER TABLE registration_invites NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE registration_invites DISABLE ROW LEVEL SECURITY")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE registration_invites TO anon, authenticated")
    op.execute("DROP INDEX IF EXISTS uq_registration_invites_active_email")
    op.drop_index("ix_registration_invites_expires_at", table_name="registration_invites")
    op.drop_index("ix_registration_invites_invited_by_id", table_name="registration_invites")
    op.drop_index("ix_registration_invites_token_hash", table_name="registration_invites")
    op.drop_index("ix_registration_invites_email", table_name="registration_invites")
    op.drop_table("registration_invites")
