"""Add recipient email to invitation code

Revision ID: add_invitation_recipient_email
Revises: 920b88e6f5b5
Create Date: 2026-02-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_invitation_recipient_email'
down_revision = '920b88e6f5b5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('invitation_code', sa.Column('recipient_email', sa.String(200), nullable=True))


def downgrade():
    op.drop_column('invitation_code', 'recipient_email')
