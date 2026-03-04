"""Add premium_google_books_enabled flag to tenant

Revision ID: d234567890ab
Revises: c123456789ab
Create Date: 2026-03-03 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd234567890ab'
down_revision = 'c123456789ab'
branch_labels = None
depends_on = None


def upgrade():
    # add new boolean column with default False (server-side default for existing rows)
    with op.batch_alter_table('tenant', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('premium_google_books_enabled', sa.Boolean(), nullable=False, server_default=sa.false())
        )
        # remove server_default to match model default
        batch_op.alter_column('premium_google_books_enabled', server_default=None)


def downgrade():
    with op.batch_alter_table('tenant', schema=None) as batch_op:
        batch_op.drop_column('premium_google_books_enabled')
