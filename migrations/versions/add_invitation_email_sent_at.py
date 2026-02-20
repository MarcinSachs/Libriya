"""Add email_sent_at to invitation_code

Revision ID: add_invitation_email_sent_at
Revises: add_invitation_recipient_email
Create Date: 2026-02-20 00:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_invitation_email_sent_at'
down_revision = 'add_invitation_recipient_email'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('invitation_code', sa.Column('email_sent_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('invitation_code', 'email_sent_at')
