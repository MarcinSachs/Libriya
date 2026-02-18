"""
Merge migration to resolve cycles in history
Revision ID: merge_resolve_cycle
Revises: 1495638fbb48,27ad0c4ba539,42404df2530c,42bd4f2a029b,58947c6ef9f7,6e53fc0c06b1,80c2cb49fa42,873d72b6bc6f,8904ea11c501,add_admin_super_admin_messaging,123456789abc,add_contact_message_id,add_contact_message_table,add_invitation_codes,add_library_loan_overdue_days,add_premium_features,add_subdomain_to_tenant,add_user_names,b1c7781652f9,c2477abce1cb,ee2182cf18f2,f1215d41dff2,make_isbn_nullable,make_tenant_id_nullable_for_user,multi_tenant_2026,simple_password_hash_fix,update_contact_msg_conv
Create Date: 2026-02-18
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_resolve_cycle'
down_revision = (
    '1495638fbb48','27ad0c4ba539','42404df2530c','42bd4f2a029b','58947c6ef9f7','6e53fc0c06b1','80c2cb49fa42',
    '873d72b6bc6f','8904ea11c501','add_admin_super_admin_messaging','123456789abc','add_contact_message_id',
    'add_contact_message_table','add_invitation_codes','add_library_loan_overdue_days','add_premium_features',
    'add_subdomain_to_tenant','add_user_names','b1c7781652f9','c2477abce1cb','ee2182cf18f2','f1215d41dff2','make_isbn_nullable',
    'make_tenant_id_nullable_for_user','multi_tenant_2026','simple_password_hash_fix','update_contact_msg_conv','000000000001'
)
branch_labels = None
depends_on = None


def upgrade():
    # This is a no-op merge migration to unify multiple heads into one.
    pass


def downgrade():
    pass
