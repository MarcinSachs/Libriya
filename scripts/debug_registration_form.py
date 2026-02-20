from app import create_app, db
from app.models import Tenant, InvitationCode, User, Library
from app.forms import RegistrationForm
from datetime import datetime, timedelta

app = create_app()
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
app.config['TESTING'] = True

with app.app_context():
    db.create_all()
    tenant = Tenant(name='T1', subdomain='t1')
    db.session.add(tenant)
    db.session.commit()
    lib = Library(name='L1', tenant_id=tenant.id)
    db.session.add(lib)
    db.session.commit()
    user = User(username='u1', email='u1@example.com', role='admin', tenant_id=tenant.id)
    user.set_password('password')
    db.session.add(user)
    db.session.commit()
    inv = InvitationCode(code='ABCD1234', created_by_id=user.id, library_id=lib.id, tenant_id=tenant.id, expires_at=datetime.utcnow()+timedelta(days=1))
    db.session.add(inv)
    db.session.commit()

    with app.test_request_context('/'):
        form = RegistrationForm(data={'create_new_tenant':'false','invitation_code':'ABCD1234','email':'b@b.com','username':'usery','password':'Str0ngPass!23','password_confirm':'Str0ngPass!23','first_name':'','last_name':''})
        print('create_new_tenant.data ->', repr(form.create_new_tenant.data))
        print('first_name.data ->', repr(form.first_name.data))
        print('last_name.data ->', repr(form.last_name.data))
        print('has validate_first_name?', hasattr(form, 'validate_first_name'))
        print('calling validate...')
        print('form.validate() ->', form.validate())
        print('form.errors ->', form.errors)
