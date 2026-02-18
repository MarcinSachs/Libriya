"""
Add updated_at column to tenant
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_tenant_updated_at'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add updated_at column (nullable) and set existing rows to created_at
    op.add_column('tenant', sa.Column('updated_at', sa.DateTime(), nullable=True))
    try:
        op.execute("UPDATE tenant SET updated_at = created_at")
    except Exception:
        # Some backends (e.g., SQLite) may fail if table empty; ignore
        pass


def downgrade():
    op.drop_column('tenant', 'updated_at')
