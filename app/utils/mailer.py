from typing import Optional
from flask import current_app
import smtplib
from email.message import EmailMessage
import os


def _send_email(to_address: str, subject: str, body: str) -> bool:
    app = current_app._get_current_object() if current_app else None
    sender = None

    if app:
        # Prefer app config, fall back to environment variables so .env works
        sender = app.config.get('MAIL_DEFAULT_SENDER') or os.environ.get('MAIL_DEFAULT_SENDER')
        mail_server = app.config.get('MAIL_SERVER') or os.environ.get('MAIL_SERVER')
        mail_port = app.config.get('MAIL_PORT') or os.environ.get('MAIL_PORT')
        mail_username = app.config.get('MAIL_USERNAME') or os.environ.get('MAIL_USERNAME')
        mail_password = app.config.get('MAIL_PASSWORD') or os.environ.get('MAIL_PASSWORD')
        use_tls = app.config.get('MAIL_USE_TLS') if 'MAIL_USE_TLS' in app.config else os.environ.get('MAIL_USE_TLS')
        use_ssl = app.config.get('MAIL_USE_SSL') if 'MAIL_USE_SSL' in app.config else os.environ.get('MAIL_USE_SSL')

        try:
            mail_port = int(mail_port) if mail_port else 0
        except Exception:
            mail_port = 0

        # Normalize boolean-like values coming from env
        def _to_bool(v):
            if v is None:
                return False
            if isinstance(v, bool):
                return v
            return str(v).lower() in ('1', 'true', 'yes', 'on')

        use_tls = _to_bool(use_tls)
        use_ssl = _to_bool(use_ssl)

        if not mail_server or not mail_port:
            # Not configured - fallback to printing for development
            print(f"[mailer] MAIL_SERVER not configured. Email to {to_address}: {subject}\n{body}")
            return True

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = sender or mail_username or 'no-reply@localhost'
        msg['To'] = to_address
        msg.set_content(body)

        try:
            if use_ssl:
                with smtplib.SMTP_SSL(mail_server, mail_port) as server:
                    if mail_username and mail_password:
                        server.login(mail_username, mail_password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(mail_server, mail_port) as server:
                    server.ehlo()
                    if use_tls:
                        server.starttls()
                        server.ehlo()
                    if mail_username and mail_password:
                        server.login(mail_username, mail_password)
                    server.send_message(msg)
            return True
        except Exception as e:
            print(f"[mailer] Error sending email: {e}")
            raise

    # No Flask context - fallback
    print(f"[mailer] No app context. Email to {to_address}: {subject}\n{body}")
    return True


def send_generic_email(to_address: str, subject: str, body: str) -> bool:
    return _send_email(to_address, subject, body)


def send_password_reset_email(user, reset_url: str) -> bool:
    subject = 'Password reset request'
    body = f"Hello {user.username},\n\nYou requested a password reset. Use the link below to reset your password:\n\n{reset_url}\n\nIf you did not request this, you can ignore this message.\n\n--\nLibriya"
    return _send_email(user.email, subject, body)
