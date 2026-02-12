"""
Add description field to Book model

Revision ID: 123456789abc
Revises: b1c7781652f9
Create Date: 2026-02-12 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '123456789abc'
down_revision = 'b1c7781652f9'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('book', sa.Column('description', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('book', 'description')
