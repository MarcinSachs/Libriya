"""Add first_name and last_name to User

Revision ID: add_user_names
Revises: add_invitation_codes
Create Date: 2026-01-27 12:01:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_user_names'
down_revision = 'add_invitation_codes'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('first_name', sa.String(50), nullable=True))
    op.add_column('user', sa.Column('last_name', sa.String(50), nullable=True))


def downgrade():
    op.drop_column('user', 'last_name')
    op.drop_column('user', 'first_name')
