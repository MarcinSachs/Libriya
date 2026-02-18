"""
Merge heads: add_password_reset_token + add_tenant_status
"""
from alembic import op
# revision identifiers, used by Alembic.
revision = 'merge_add_passwordreset_and_tenantstatus'
down_revision = ('add_password_reset_token', 'add_tenant_status')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
