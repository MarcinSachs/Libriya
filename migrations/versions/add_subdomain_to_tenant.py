"""
Add subdomain and created_at columns to Tenant model
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

revision = 'add_subdomain_to_tenant'
down_revision = '6e53fc0c06b1'
branch_labels = None
depends_on = None


def upgrade():
    # Add subdomain column (nullable initially)
    op.add_column('tenant', sa.Column('subdomain', sa.String(100), nullable=True))

    # Add created_at column
    op.add_column('tenant', sa.Column('created_at', sa.DateTime(), nullable=True))

    # Set default subdomain for existing tenants (convert name to subdomain format)
    op.execute("""
        UPDATE tenant 
        SET subdomain = LOWER(REPLACE(REPLACE(name, ' ', '-'), '_', '-'))
        WHERE subdomain IS NULL
    """)

    # Set created_at for existing tenants (dialect-aware)
    conn = op.get_bind()
    if conn.dialect.name == 'sqlite':
        op.execute("""
            UPDATE tenant 
            SET created_at = datetime('now')
            WHERE created_at IS NULL
        """)
    else:
        # MySQL/MariaDB: use NOW()
        op.execute("""
            UPDATE tenant 
            SET created_at = NOW()
            WHERE created_at IS NULL
        """)

    # Add unique constraint using batch mode for SQLite
    with op.batch_alter_table('tenant', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_tenant_subdomain', ['subdomain'])


def downgrade():
    with op.batch_alter_table('tenant', schema=None) as batch_op:
        batch_op.drop_constraint('uq_tenant_subdomain', type_='unique')
        batch_op.drop_column('subdomain')
        batch_op.drop_column('created_at')
