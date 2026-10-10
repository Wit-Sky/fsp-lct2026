"""profile: roles and soft skills (ТЗ 2.1, разбор резюме)

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-11 03:40:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default — чтобы у уже существующих профилей были пустые списки, а не NULL
    with op.batch_alter_table('candidate_profiles') as batch:
        batch.add_column(sa.Column('roles', sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
        batch.add_column(sa.Column('soft_skills', sa.JSON(), nullable=False, server_default=sa.text("'[]'")))


def downgrade() -> None:
    with op.batch_alter_table('candidate_profiles') as batch:
        batch.drop_column('soft_skills')
        batch.drop_column('roles')
