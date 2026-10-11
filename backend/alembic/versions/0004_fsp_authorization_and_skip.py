"""Одноразовое связывание ФСП без JWT в URL и сохранение шага ФСП в профиле.

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("candidate_profiles", sa.Column("fsp_skipped", sa.Boolean(), nullable=False,
                                                server_default=sa.false()))
    op.create_table(
        "fsp_authorizations",
        sa.Column("code_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("browser_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state_hash", sa.String(64), nullable=True, unique=True),
        sa.Column("state_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_fsp_authorizations_user_id", "fsp_authorizations", ["user_id"])


def downgrade() -> None:
    op.drop_table("fsp_authorizations")
    with op.batch_alter_table("candidate_profiles") as batch:
        batch.drop_column("fsp_skipped")
