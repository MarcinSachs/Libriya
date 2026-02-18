"""Add is_email_verified column to user table

Revision ID: add_email_verification_column
Revises: merge_manual_unify_heads
Create Date: 2026-02-18
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_email_verification_column'
down_revision = 'merge_manual_unify_heads'
branch_labels = None
depends_on = None


def upgrade():
    # Add is_email_verified column with default False
    op.add_column('user', sa.Column('is_email_verified', sa.Boolean(), nullable=False, server_default=sa.true()))
    
    # Mark all existing users as verified (they are already in the system)
    op.execute('UPDATE user SET is_email_verified = True')


def downgrade():
    # Remove the column
    op.drop_column('user', 'is_email_verified')
