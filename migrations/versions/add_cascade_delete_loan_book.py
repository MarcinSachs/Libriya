"""Add cascade delete to loan.book_id foreign key

Revision ID: add_cascade_delete_loan_book
Revises: add_comment_tenant_id
Create Date: 2026-02-19 21:57:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_cascade_delete_loan_book'
down_revision = 'add_comment_tenant_id'
branch_labels = None
depends_on = None


def upgrade():
    # Drop existing foreign key constraint
    op.drop_constraint('loan_ibfk_1', 'loan', type_='foreignkey')

    # Create new foreign key with CASCADE DELETE
    op.create_foreign_key(
        'loan_ibfk_1',
        'loan',
        'book',
        ['book_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade():
    # Drop foreign key with CASCADE DELETE
    op.drop_constraint('loan_ibfk_1', 'loan', type_='foreignkey')

    # Recreate original foreign key without CASCADE DELETE
    op.create_foreign_key(
        'loan_ibfk_1',
        'loan',
        'book',
        ['book_id'],
        ['id']
    )
