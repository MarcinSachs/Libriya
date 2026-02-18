"""Add invitation codes for user registration

Revision ID: add_invitation_codes
Revises: ee2182cf18f2
Create Date: 2026-01-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_invitation_codes'
down_revision = 'ee2182cf18f2'
branch_labels = None
depends_on = None


def upgrade():
    # Create invitation_code table
    op.create_table('invitation_code',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('code', sa.String(8), nullable=False),
                    sa.Column('created_by_id', sa.Integer(), nullable=False),
                    sa.Column('library_id', sa.Integer(), nullable=False),
                    sa.Column('used_by_id', sa.Integer(), nullable=True),
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('expires_at', sa.DateTime(), nullable=True),
                    sa.Column('used_at', sa.DateTime(), nullable=True),
                    sa.ForeignKeyConstraint(['created_by_id'], ['user.id'], ),
                    sa.ForeignKeyConstraint(['library_id'], ['library.id'], ),
                    sa.ForeignKeyConstraint(['used_by_id'], ['user.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_invitation_code_code'), 'invitation_code', ['code'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_invitation_code_code'), table_name='invitation_code')
    op.drop_table('invitation_code')
