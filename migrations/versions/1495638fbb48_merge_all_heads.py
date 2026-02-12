"""Merge all heads

Revision ID: 1495638fbb48
Revises: 27ad0c4ba539, 123456789abc
Create Date: 2026-02-12 20:12:37.231273

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1495638fbb48'
down_revision = ('27ad0c4ba539', '123456789abc')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
