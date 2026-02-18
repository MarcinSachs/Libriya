"""
Add AdminSuperAdminConversation and AdminSuperAdminMessage models for messaging between tenant admins and super-admin
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

revision = 'add_admin_super_admin_messaging'
down_revision = 'make_tenant_id_nullable_for_user'
branch_labels = None
depends_on = None

def upgrade():
    # Create AdminSuperAdminConversation table
    op.create_table(
        'admin_super_admin_conversation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('admin_id', sa.Integer(), nullable=False),
        sa.Column('subject', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ),
        sa.ForeignKeyConstraint(['admin_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_admin_super_admin_conversation_tenant_id', 'admin_super_admin_conversation', ['tenant_id'])
    op.create_index('ix_admin_super_admin_conversation_admin_id', 'admin_super_admin_conversation', ['admin_id'])
    op.create_index('ix_admin_super_admin_conversation_created_at', 'admin_super_admin_conversation', ['created_at'])
    
    # Create AdminSuperAdminMessage table
    op.create_table(
        'admin_super_admin_message',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('read', sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['admin_super_admin_conversation.id'], ),
        sa.ForeignKeyConstraint(['sender_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_admin_super_admin_message_conversation_id', 'admin_super_admin_message', ['conversation_id'])
    op.create_index('ix_admin_super_admin_message_sender_id', 'admin_super_admin_message', ['sender_id'])
    op.create_index('ix_admin_super_admin_message_created_at', 'admin_super_admin_message', ['created_at'])


def downgrade():
    op.drop_index('ix_admin_super_admin_message_created_at', 'admin_super_admin_message')
    op.drop_index('ix_admin_super_admin_message_sender_id', 'admin_super_admin_message')
    op.drop_index('ix_admin_super_admin_message_conversation_id', 'admin_super_admin_message')
    op.drop_table('admin_super_admin_message')
    
    op.drop_index('ix_admin_super_admin_conversation_created_at', 'admin_super_admin_conversation')
    op.drop_index('ix_admin_super_admin_conversation_admin_id', 'admin_super_admin_conversation')
    op.drop_index('ix_admin_super_admin_conversation_tenant_id', 'admin_super_admin_conversation')
    op.drop_table('admin_super_admin_conversation')
