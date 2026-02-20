"""Add shared links table

Revision ID: add_shared_link
Revises: add_invitation_email_sent_at
Create Date: 2026-02-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_shared_link'
down_revision = 'add_invitation_email_sent_at'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'shared_link',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('library_id', sa.Integer(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['library_id'], ['library.id'], ),
        sa.ForeignKeyConstraint(['created_by_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_shared_link_token'), 'shared_link', ['token'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_shared_link_token'), table_name='shared_link')
    op.drop_table('shared_link')
