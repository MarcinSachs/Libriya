"""
Add loan_overdue_days column to library
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_library_loan_overdue_days'
down_revision = 'c2477abce1cb'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('library', sa.Column('loan_overdue_days', sa.Integer(), nullable=False, server_default='14'))


def downgrade():
    op.drop_column('library', 'loan_overdue_days')
