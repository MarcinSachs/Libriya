"""Merge heads for tenant limits and previous branch

Revision ID: 20260219_merge_heads_limits
Revises: 20260219_add_tenant_limits, merge_all_heads_fix
Create Date: 2026-02-19
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260219_merge_heads_limits'
down_revision = ('20260219_add_tenant_limits', 'merge_all_heads_fix')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
