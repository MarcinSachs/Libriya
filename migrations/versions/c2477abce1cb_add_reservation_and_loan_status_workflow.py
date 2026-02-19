"""Add reservation and loan status workflow

Revision ID: c2477abce1cb
Revises: 42bd4f2a029b
Create Date: 2025-08-06 09:32:34.287744

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = 'c2477abce1cb'
down_revision = '42bd4f2a029b'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # --- Zmiany dla tabeli 'book' ---
    # 1. Dodaj nową kolumnę 'status'. Ustaw ją tymczasowo jako nullable.
    op.add_column('book', sa.Column('status', sa.String(length=50), nullable=True))

    # 2. Zaktualizuj nową kolumnę 'status' na podstawie starej 'is_available'.
    #    Te operacje muszą nastąpić, zanim 'is_available' zostanie usunięta.
    conn.execute(text("UPDATE book SET status = 'available' WHERE is_available = 1"))
    conn.execute(text("UPDATE book SET status = 'on_loan' WHERE is_available = 0"))

    # 3. Usuń starą kolumnę 'is_available'.
    op.drop_column('book', 'is_available')

    # 4. Zmień kolumnę 'status' na NOT NULL i ustaw domyślną wartość, jeśli jest to konieczne.
    #    Używamy batch_alter_table, ponieważ zmiana nullability na SQLite może wymagać przebudowy tabeli.
    with op.batch_alter_table('book', schema=None) as batch_op:
        batch_op.alter_column('status',
                              existing_type=sa.String(length=50),
                              nullable=False,
                              server_default='available')


    # --- Zmiany dla tabeli 'loan' ---
    with op.batch_alter_table('loan', schema=None) as batch_op:
        # Zmień nazwę kolumny loan_date na reservation_date
        batch_op.alter_column('loan_date',
                              new_column_name='reservation_date',
                              existing_type=sa.DateTime(),
                              nullable=True) # Zachowaj nullable zgodnie z poprzednim stanem

        # Dodaj nową kolumnę issue_date
        batch_op.add_column(sa.Column('issue_date', sa.DateTime(), nullable=True))

        # Dodaj nową kolumnę status, tymczasowo jako nullable
        batch_op.add_column(sa.Column('status', sa.String(length=50), nullable=True)) # Temporarily nullable for update

    # 2. Zaktualizuj statusy wypożyczeń i ustaw issue_date dla istniejących danych.
    #    Te UPDATE'y wykonujemy po dodaniu kolumn, ale przed ustawieniem ich na NOT NULL.
    conn.execute(text("UPDATE loan SET status = 'active', issue_date = reservation_date WHERE return_date IS NULL"))
    conn.execute(text("UPDATE loan SET status = 'returned', issue_date = reservation_date WHERE return_date IS NOT NULL"))

    # 3. Zmień kolumnę 'status' w tabeli 'loan' na NOT NULL i ustaw domyślną wartość.
    with op.batch_alter_table('loan', schema=None) as batch_op:
        batch_op.alter_column('status',
                              existing_type=sa.String(length=50),
                              nullable=False,
                              server_default='pending')


def downgrade():
    conn = op.get_bind()

    # --- Przywracanie zmian dla tabeli 'loan' ---
    with op.batch_alter_table('loan', schema=None) as batch_op:
        # Przywróć kolumnę status do nullable (jeśli była taka pierwotnie) przed usunięciem
        batch_op.alter_column('status', existing_type=sa.String(length=50), nullable=True) # Adjust nullable based on original Loan model
        batch_op.drop_column('status')
        batch_op.drop_column('issue_date')
        # Przywróć nazwę kolumny reservation_date na loan_date
        batch_op.alter_column('reservation_date',
                              new_column_name='loan_date',
                              existing_type=sa.DateTime(),
                              nullable=True) # Adjust nullable based on original Loan model


    # --- Przywracanie zmian dla tabeli 'book' ---
    # 1. Dodaj z powrotem kolumnę 'is_available'. Ustaw ją tymczasowo jako nullable.
    op.add_column('book', sa.Column('is_available', sa.BOOLEAN(), nullable=True))

    # 2. Zaktualizuj 'is_available' na podstawie 'status'.
    conn.execute(text("UPDATE book SET is_available = 1 WHERE status = 'available'"))
    conn.execute(text("UPDATE book SET is_available = 0 WHERE status IN ('on_loan', 'reserved', 'pending', 'active', 'returned', 'cancelled')")) # Obejmij wszystkie stany, które nie są 'available'

    # 3. Usuń kolumnę 'status'.
    op.drop_column('book', 'status')

    # 4. Zmień kolumnę 'is_available' na jej pierwotne właściwości (NOT NULL, server_default).
    with op.batch_alter_table('book', schema=None) as batch_op:
        batch_op.alter_column('is_available',
                              existing_type=sa.BOOLEAN(),
                              nullable=True, # Zmień na False, jeśli pierwotnie było NOT NULL
                              server_default=sa.text('1')) # Ustaw domyślny status