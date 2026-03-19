"""Make username unique per tenant instead of globally

Revision ID: e345678901ab
Revises: d234567890ab
Create Date: 2026-03-19 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e345678901ab'
down_revision = ('d234567890ab', 'a8658df6c988')
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        # Drop the old globally-unique index on username alone
        batch_op.drop_index('ix_user_username')
        # Create a composite unique constraint: one username per tenant
        batch_op.create_unique_constraint(
            'uq_user_username_tenant', ['username', 'tenant_id']
        )
        # Recreate a plain (non-unique) index on username for fast login lookups
        batch_op.create_index('ix_user_username', ['username'], unique=False)


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_index('ix_user_username')
        batch_op.drop_constraint('uq_user_username_tenant', type_='unique')
        # Restore the original globally-unique index
        batch_op.create_index('ix_user_username', ['username'], unique=True)
