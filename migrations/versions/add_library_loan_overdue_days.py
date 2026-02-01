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
    # Kolumna loan_overdue_days już istnieje w modelu
    # Ta migracja jest tylko dla spójności historii migracji
    pass


def downgrade():
    op.drop_column('library', 'loan_overdue_days')
