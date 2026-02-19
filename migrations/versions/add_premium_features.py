"""Add premium features to tenant model.

Revision ID: add_premium_features
Revises: 6e53fc0c06b1
Create Date: 2026-02-17 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_premium_features'
down_revision = 'add_admin_super_admin_messaging'
branch_labels = None
depends_on = None


def upgrade():
    # Add premium feature columns to tenant table
    with op.batch_alter_table('tenant', schema=None) as batch_op:
        batch_op.add_column(sa.Column('premium_bookcover_enabled', sa.Boolean(),
                            nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('premium_biblioteka_narodowa_enabled',
                            sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    # Remove premium feature columns from tenant table
    with op.batch_alter_table('tenant', schema=None) as batch_op:
        batch_op.drop_column('premium_biblioteka_narodowa_enabled')
        batch_op.drop_column('premium_bookcover_enabled')


"""Stub migration to restore missing revision 'add_premium_features'

Revision ID: add_premium_features
Revises: 000000000001
Create Date: 2026-02-19 13:54:00.000000
"""

# revision identifiers, used by Alembic.
revision = 'add_premium_features'
down_revision = '000000000001'
branch_labels = None
depends_on = None


def upgrade():
    # no-op stub
    pass


def downgrade():
    pass
