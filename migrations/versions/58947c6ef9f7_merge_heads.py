"""merge heads

Revision ID: 58947c6ef9f7
Revises: 42404df2530c, make_isbn_nullable
Create Date: 2026-01-31 14:58:57.488087

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '58947c6ef9f7'
down_revision = ('42404df2530c', 'make_isbn_nullable')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
