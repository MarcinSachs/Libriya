"""Make book.year nullable

Revision ID: c123456789ab
Revises: b6abb05c0cb1
Create Date: 2026-03-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c123456789ab'
down_revision = 'b6abb05c0cb1'
branch_labels = None
depends_on = None


def upgrade():
    # make the year column nullable so books can be stored without a year
    with op.batch_alter_table('book', schema=None) as batch_op:
        batch_op.alter_column('year',
                              existing_type=sa.Integer(),
                              nullable=True)


def downgrade():
    # revert to non-nullable (existing data must have year values)
    with op.batch_alter_table('book', schema=None) as batch_op:
        batch_op.alter_column('year',
                              existing_type=sa.Integer(),
                              nullable=False)
