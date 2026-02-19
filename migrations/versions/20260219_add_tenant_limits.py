"""add max_libraries and max_books to tenant

Revision ID: 20260219_add_tenant_limits
Revises: 1495638fbb48
Create Date: 2026-02-19
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260219_add_tenant_limits'
down_revision = '1495638fbb48'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('tenant', sa.Column('max_libraries', sa.Integer(), nullable=True))
    op.add_column('tenant', sa.Column('max_books', sa.Integer(), nullable=True))
    # Set default values for existing tenants (1 library, 10 books)
    op.execute("UPDATE tenant SET max_libraries=1 WHERE max_libraries IS NULL")
    op.execute("UPDATE tenant SET max_books=10 WHERE max_books IS NULL")

def downgrade():
    op.drop_column('tenant', 'max_libraries')
    op.drop_column('tenant', 'max_books')
