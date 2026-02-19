"""Merge current heads into a single head (repair)

Revision ID: merge_all_heads_fix
Revises: 1495638fbb48, simple_password_hash_fix
Create Date: 2026-02-19 14:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'merge_all_heads_fix'
down_revision = ('1495638fbb48', 'simple_password_hash_fix')
branch_labels = None
depends_on = None


def upgrade():
    # merge stub: no-op
    pass


def downgrade():
    pass
