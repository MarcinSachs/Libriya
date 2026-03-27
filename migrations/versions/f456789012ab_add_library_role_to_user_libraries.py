"""Add library_role column to user_libraries

Revision ID: f456789012ab
Revises: e345678901ab
Create Date: 2026-03-27 00:00:00.000000

Adds a per-library role to the user_libraries association table.
  'member'  – read/borrow access only (default for all existing rows)
  'manager' – can manage books, loans and users in this library

Existing rows for users with role='manager' are promoted to
library_role='manager' so behaviour stays unchanged after the migration.
"""
from alembic import op
import sqlalchemy as sa

revision = 'f456789012ab'
down_revision = 'e345678901ab'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user_libraries', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('library_role', sa.String(20), nullable=False, server_default='member')
        )

    # Promote existing managers: wherever a user has role='manager',
    # set library_role='manager' for all their library memberships.
    op.execute(
        "UPDATE user_libraries "
        "SET library_role = 'manager' "
        "WHERE user_id IN (SELECT id FROM user WHERE role = 'manager')"
    )


def downgrade():
    with op.batch_alter_table('user_libraries', schema=None) as batch_op:
        batch_op.drop_column('library_role')
