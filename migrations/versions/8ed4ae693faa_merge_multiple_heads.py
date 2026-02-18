"""merge multiple heads

Revision ID: 8ed4ae693faa
Revises: add_audit_logfile, simple_password_hash_fix
Create Date: 2026-02-18 07:54:44.578357

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8ed4ae693faa'
down_revision = ('add_audit_logfile', 'simple_password_hash_fix')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
