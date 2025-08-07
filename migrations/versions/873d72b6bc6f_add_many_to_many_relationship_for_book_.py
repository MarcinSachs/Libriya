"""Add many-to-many relationship for book genres

Revision ID: 873d72b6bc6f
Revises: f1215d41dff2
Create Date: 2025-08-07 09:17:15.144926

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '873d72b6bc6f'
down_revision = 'f1215d41dff2'
branch_labels = None
depends_on = None


# Wersja z `drop_column` zamiast `drop_constraint`
def upgrade():
    with op.batch_alter_table('book', schema=None) as batch_op:
        batch_op.drop_column('genre_id') # To powinno usunąć kolumnę i powiązany klucz obcy

    op.create_table(
        'book_genres',
        sa.Column('book_id', sa.Integer(), nullable=False),
        sa.Column('genre_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['book_id'], ['book.id'], ),
        sa.ForeignKeyConstraint(['genre_id'], ['genre.id'], ),
        sa.PrimaryKeyConstraint('book_id', 'genre_id')
    )

def downgrade():
    op.drop_table('book_genres')

    with op.batch_alter_table('book', schema=None) as batch_op:
        batch_op.add_column(sa.Column('genre_id', sa.INTEGER(), nullable=False))
        batch_op.create_foreign_key('fk_book_genre_id', 'genre', ['genre_id'], ['id'])
    # ### end Alembic commands ###