"""Empty initial migration created by scripts/reset_migrations.py

Revision ID: 000000000001
Revises: 
Create Date: 2026-02-19T13:54:04.089432Z
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '000000000001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # no-op: database schema will be created via SQLAlchemy create_all()
    pass


def downgrade():
    pass
