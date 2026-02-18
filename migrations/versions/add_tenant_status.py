"""
Add status column to tenant
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_tenant_status'
down_revision = '1b3373e73a8c'
branch_labels = None
depends_on = None


def upgrade():
    # Add status column with default 'active'
    op.add_column('tenant', sa.Column('status', sa.String(length=50), nullable=False, server_default='active'))
    try:
        # remove server_default if desired
        op.alter_column('tenant', 'status', server_default=None)
    except Exception:
        pass


def downgrade():
    op.drop_column('tenant', 'status')
