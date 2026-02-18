"""merge add_tenant_updated_at

Revision ID: 1b3373e73a8c
Revises: 8ed4ae693faa, add_tenant_updated_at
Create Date: 2026-02-18 08:00:55.047487

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1b3373e73a8c'
down_revision = ('8ed4ae693faa', 'add_tenant_updated_at')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
