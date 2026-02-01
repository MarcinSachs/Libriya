"""add_contact_message_table

Revision ID: add_contact_message_table
Revises: b1c7781652f9
Create Date: 2026-02-01

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_contact_message_table'
down_revision = 'b1c7781652f9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'contact_message',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True),
        sa.Column('email', sa.String(length=120), nullable=True),
        sa.Column('subject', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('contact_message')
