from typing import Optional
from flask import current_app
import smtplib
from email.message import EmailMessage


def send_password_reset_email(user, reset_url: str) -> bool:
    """Send password reset email to user using SMTP settings from app config.

    Config variables used (set these in your environment or config):
      - MAIL_SERVER
      - MAIL_PORT
      - MAIL_USERNAME
      - MAIL_PASSWORD
      - MAIL_USE_TLS (bool, optional)
      - MAIL_USE_SSL (bool, optional)
      - MAIL_DEFAULT_SENDER (email address)

    Falls back to printing the URL when MAIL_SERVER is not configured (useful
    for local development).
    """
    app = current_app._get_current_object() if current_app else None
    sender = None
    subject = 'Password reset request'
    body = f"Hello {user.username},\n\nYou requested a password reset. Use the link below to reset your password:\n\n{reset_url}\n\nIf you did not request this, you can ignore this message.\n\n--\nLibriya"

    if app:
        sender = app.config.get('MAIL_DEFAULT_SENDER')
        mail_server = app.config.get('MAIL_SERVER')
        mail_port = int(app.config.get('MAIL_PORT', 0) or 0)
        mail_username = app.config.get('MAIL_USERNAME')
        mail_password = app.config.get('MAIL_PASSWORD')
        use_tls = bool(app.config.get('MAIL_USE_TLS', False))
        use_ssl = bool(app.config.get('MAIL_USE_SSL', False))

        if not mail_server or not mail_port:
            # Not configured - fallback to printing for development
            print(f"[mailer] MAIL_SERVER not configured. Password reset for {user.email}: {reset_url}")
            return True

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = sender or mail_username or 'no-reply@localhost'
        msg['To'] = user.email
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
            # In production you might want to log this exception
            print(f"[mailer] Error sending email: {e}")
            raise

    # No Flask context - fallback
    print(f"[mailer] No app context. Password reset for {user.email}: {reset_url}")
    return True
