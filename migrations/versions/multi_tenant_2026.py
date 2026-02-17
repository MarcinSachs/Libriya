"""
Alembic migration for multi-tenant support:
- Adds tenant_id columns to User, Library, Book, Loan, InvitationCode
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = 'multi_tenant_2026'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Step 0: Jeśli tablica tenant nie istnieje, utwórz ją
    op.create_table('tenant',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Dodaj domyślny tenant jeśli nie istnieje
    op.execute("INSERT OR IGNORE INTO tenant (id, name) VALUES (1, 'default')")
    
    # Step 1: Dodaj tenant_id kolumny bez constraints (nullable)
    op.add_column('user', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.add_column('library', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.add_column('book', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.add_column('loan', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.add_column('invitation_code', sa.Column('tenant_id', sa.Integer(), nullable=True))
    
    # Step 2: Ustaw domyślną wartość tenant_id dla istniejących rekordów (np. 1)
    op.execute('UPDATE user SET tenant_id = 1 WHERE tenant_id IS NULL')
    op.execute('UPDATE library SET tenant_id = 1 WHERE tenant_id IS NULL')
    op.execute('UPDATE book SET tenant_id = 1 WHERE tenant_id IS NULL')
    op.execute('UPDATE loan SET tenant_id = 1 WHERE tenant_id IS NULL')
    op.execute('UPDATE invitation_code SET tenant_id = 1 WHERE tenant_id IS NULL')
    
    # Step 3: Zmień kolumny na NOT NULL w batch mode
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('tenant_id', nullable=False)
        batch_op.create_foreign_key('fk_user_tenant_id', 'tenant', ['tenant_id'], ['id'])
    
    with op.batch_alter_table('library', schema=None) as batch_op:
        batch_op.alter_column('tenant_id', nullable=False)
        batch_op.create_foreign_key('fk_library_tenant_id', 'tenant', ['tenant_id'], ['id'])
    
    with op.batch_alter_table('book', schema=None) as batch_op:
        batch_op.alter_column('tenant_id', nullable=False)
        batch_op.create_foreign_key('fk_book_tenant_id', 'tenant', ['tenant_id'], ['id'])
    
    with op.batch_alter_table('loan', schema=None) as batch_op:
        batch_op.alter_column('tenant_id', nullable=False)
        batch_op.create_foreign_key('fk_loan_tenant_id', 'tenant', ['tenant_id'], ['id'])
    
    with op.batch_alter_table('invitation_code', schema=None) as batch_op:
        batch_op.alter_column('tenant_id', nullable=False)
        batch_op.create_foreign_key('fk_invitation_code_tenant_id', 'tenant', ['tenant_id'], ['id'])


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_constraint('fk_user_tenant_id', type_='foreignkey')
        batch_op.drop_column('tenant_id')
    
    with op.batch_alter_table('library', schema=None) as batch_op:
        batch_op.drop_constraint('fk_library_tenant_id', type_='foreignkey')
        batch_op.drop_column('tenant_id')
    
    with op.batch_alter_table('book', schema=None) as batch_op:
        batch_op.drop_constraint('fk_book_tenant_id', type_='foreignkey')
        batch_op.drop_column('tenant_id')
    
    with op.batch_alter_table('loan', schema=None) as batch_op:
        batch_op.drop_constraint('fk_loan_tenant_id', type_='foreignkey')
        batch_op.drop_column('tenant_id')
    
    with op.batch_alter_table('invitation_code', schema=None) as batch_op:
        batch_op.drop_constraint('fk_invitation_code_tenant_id', type_='foreignkey')
        batch_op.drop_column('tenant_id')
    
    # Usuń tabelę tenant
    op.drop_table('tenant')
