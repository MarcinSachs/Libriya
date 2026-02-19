"""Simple fix for password_hash column size

Revision ID: simple_password_hash_fix
Revises: add_premium_features
Create Date: 2026-02-17 20:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'simple_password_hash_fix'
down_revision = 'add_premium_features'
branch_labels = None
depends_on = None


def upgrade():
    # Only modify the password_hash column - increase from 128 to 255
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('password_hash',
                              existing_type=mysql.VARCHAR(length=128),
                              type_=sa.String(length=255),
                              existing_nullable=False)


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('password_hash',
                              existing_type=sa.String(length=255),
                              type_=mysql.VARCHAR(length=128),
                              existing_nullable=False)


"""Simple fix for password_hash column size

Revision ID: simple_password_hash_fix
Revises: add_premium_features
Create Date: 2026-02-17 20:05:00.000000

"""

# revision identifiers, used by Alembic.
revision = 'simple_password_hash_fix'
down_revision = 'add_premium_features'
branch_labels = None
depends_on = None


def upgrade():
    # Only modify the password_hash column - increase from 128 to 255
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('password_hash',
                              existing_type=mysql.VARCHAR(length=128),
                              type_=sa.String(length=255),
                              existing_nullable=False)


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('password_hash',
                              existing_type=sa.String(length=255),
                              type_=mysql.VARCHAR(length=128),
                              existing_nullable=False)
