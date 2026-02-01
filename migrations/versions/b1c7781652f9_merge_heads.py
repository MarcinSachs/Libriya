"""merge heads

Revision ID: b1c7781652f9
Revises: 58947c6ef9f7, add_library_loan_overdue_days
Create Date: 2026-02-01 14:55:47.480938

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b1c7781652f9'
down_revision = ('58947c6ef9f7', 'add_library_loan_overdue_days')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
