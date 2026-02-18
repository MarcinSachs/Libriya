import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from libriya import create_app
from app import db
from app.models import User

app = create_app()

with app.app_context():
    email = 'marcinsachs@gmail.com'
    user = User.query.filter_by(email=email).first()
    if user:
        print(f'Found user: {user.username} / {user.email} (id={user.id}) - deleting')
        # Remove related password reset tokens
        try:
            from app.models import PasswordResetToken
            PasswordResetToken.query.filter_by(user_id=user.id).delete()
        except Exception:
            pass
        db.session.delete(user)
        db.session.commit()
        print('Deleted.')
    else:
        print('User not found.')
