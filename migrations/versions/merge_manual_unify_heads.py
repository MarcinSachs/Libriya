"""
Manual merge revision to ensure Alembic has a single head
Revision ID: merge_manual_unify_heads
Revises: merge_resolve_cycle, 000000000001
Create Date: 2026-02-18
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_manual_unify_heads'
down_revision = ('merge_resolve_cycle', '000000000001')
branch_labels = None
depends_on = None


def upgrade():
    # no-op merge revision
    pass


def downgrade():
    pass
