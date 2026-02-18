"""Update ContactMessage for two-way conversations

Revision ID: update_contact_msg_conv
Revises: add_contact_message_table
Create Date: 2026-02-01

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'update_contact_msg_conv'
down_revision = 'add_contact_message_table'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('contact_message', schema=None) as batch_op:
        batch_op.add_column(sa.Column('library_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('reply_message', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('reply_by_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('replied_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('read_by_admin', sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('is_resolved', sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))
        batch_op.create_foreign_key('fk_contact_message_library_id', 'library', ['library_id'], ['id'])
        batch_op.create_foreign_key('fk_contact_message_reply_by_id', 'user', ['reply_by_id'], ['id'])


def downgrade():
    op.drop_column('contact_message', 'library_id')
    op.drop_column('contact_message', 'reply_message')
    op.drop_column('contact_message', 'reply_by_id')
    op.drop_column('contact_message', 'replied_at')
    op.drop_column('contact_message', 'read_by_admin')
    op.drop_column('contact_message', 'is_resolved')
    op.drop_column('contact_message', 'updated_at')
