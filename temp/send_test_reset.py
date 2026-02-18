# Ensure project root is on sys.path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from libriya import create_app
from app import db
from app.models import User, PasswordResetToken
from app.utils.mailer import send_password_reset_email

app = create_app()

with app.app_context():
    # Use existing DB schema in instance/libriya.db; do NOT call create_all()

    email = 'marcinsachs@gmail.com'
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(username='marcinsachs_test', email=email)
        user.set_password('TempPass123!')
        db.session.add(user)
        db.session.commit()
        print(f'Created test user: {user.username} / {user.email}')
    else:
        print(f'Found existing user: {user.username} / {user.email}')

    token = PasswordResetToken.generate_token(user.id, expires_in=3600)
    reset_url = f"http://127.0.0.1:5000/auth/password-reset/confirm?token={token}"

    try:
        send_password_reset_email(user, reset_url)
        print('Send function returned without exception.')
        print('Reset URL:', reset_url)
    except Exception as e:
        print('Error sending email:', e)
