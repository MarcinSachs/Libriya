"""
Add AuditLogFile table for file-based audit log metadata
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_audit_logfile'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'audit_log_file',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('filename', sa.String(length=500), nullable=False, unique=True),
        sa.Column('start_ts', sa.DateTime(), nullable=True),
        sa.Column('end_ts', sa.DateTime(), nullable=True),
        sa.Column('size', sa.Integer(), nullable=True),
        sa.Column('archived', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )
    op.create_index(op.f('ix_audit_log_file_tenant_id'), 'audit_log_file', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_audit_log_file_filename'), 'audit_log_file', ['filename'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_audit_log_file_filename'), table_name='audit_log_file')
    op.drop_index(op.f('ix_audit_log_file_tenant_id'), table_name='audit_log_file')
    op.drop_table('audit_log_file')
