"""
Make tenant_id nullable for User to support super-admin accounts (tenant_id=NULL for super-admin)
"""
from alembic import op
import sqlalchemy as sa

revision = 'make_tenant_id_nullable_for_user'
down_revision = 'add_subdomain_to_tenant'
branch_labels = None
depends_on = None


def upgrade():
    # Make tenant_id nullable for User (super-admin won't have a tenant assigned)
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('tenant_id', existing_type=sa.Integer(), nullable=True)


def downgrade():
    # Make tenant_id non-nullable again
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('tenant_id', existing_type=sa.Integer(), nullable=False)
