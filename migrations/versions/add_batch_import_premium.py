"""Add batch_import premium feature to tenant model.

Revision ID: add_batch_import_premium
Revises: add_premium_features
Create Date: 2026-02-19 20:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_batch_import_premium'
down_revision = 'add_premium_features'
branch_labels = None
depends_on = None


def upgrade():
    # Add batch_import premium feature column to tenant table
    with op.batch_alter_table('tenant', schema=None) as batch_op:
        batch_op.add_column(sa.Column('premium_batch_import_enabled', sa.Boolean(),
                            nullable=False, server_default=sa.false()))


def downgrade():
    # Remove batch_import premium feature column from tenant table
    with op.batch_alter_table('tenant', schema=None) as batch_op:
        batch_op.drop_column('premium_batch_import_enabled')
