"""merge heads for multi-tenant

Revision ID: 6e53fc0c06b1
Revises: 1495638fbb48, multi_tenant_2026
Create Date: 2026-02-17 10:58:09.974084

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6e53fc0c06b1'
down_revision = ('1495638fbb48', 'multi_tenant_2026')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
