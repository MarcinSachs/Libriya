"""Make ISBN nullable for books without ISBN

Revision ID: make_isbn_nullable
Revises: f1215d41dff2
Create Date: 2026-01-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'make_isbn_nullable'
down_revision = 'f1215d41dff2'
branch_labels = None
depends_on = None


def upgrade():
    # Modify the isbn column to allow NULL values
    with op.batch_alter_table('book', schema=None) as batch_op:
        batch_op.alter_column('isbn',
                              existing_type=sa.String(length=13),
                              nullable=True,
                              existing_nullable=False)


def downgrade():
    # Revert the isbn column to NOT NULL
    # Note: This will fail if there are books with NULL ISBN
    with op.batch_alter_table('book', schema=None) as batch_op:
        batch_op.alter_column('isbn',
                              existing_type=sa.String(length=13),
                              nullable=False,
                              existing_nullable=True)
