from app import db
from app.models import Notification
from flask import current_app
from flask_babel import force_locale, _


def create_notification(recipients, sender, message, notification_type, loan=None, send_email=False, email_subject=None):
    """
    Create and save notifications for one or multiple recipients.

    Args:
        recipients: User object or list of User objects
        sender: User object (who triggered the notification)
        message: str (notification message)
        notification_type: str (e.g., 'reservation_request', 'loan_approved')
        loan: Loan object (optional, related loan)
        send_email: bool - if True, an email will be sent to each recipient
        email_subject: optional string overriding the email subject; if not
            provided a generic subject will be used.
    """
    if not isinstance(recipients, list):
        recipients = [recipients]

    sent_list = []
    for recipient in recipients:
        # Merge to avoid session conflicts with multiple User instances
        merged_recipient = db.session.merge(recipient)
        merged_sender = db.session.merge(sender)

        new_notification = Notification(
            recipient=merged_recipient,
            sender=merged_sender,
            message=message,
            type=notification_type,
            loan=loan
        )
        db.session.add(new_notification)

        if send_email and merged_recipient.email:
            # choose locale from user preference or fallback
            lang = getattr(merged_recipient, 'preferred_locale', None) or current_app.config.get('BABEL_DEFAULT_LOCALE')
            try:
                with force_locale(lang):
                    subj = email_subject or _('Notification from Libriya')
                    body = message
                from app.utils.mailer import send_generic_email
                send_generic_email(merged_recipient.email, subj, body)
                sent_list.append(merged_recipient.email)
            except Exception:
                # swallow errors; logging could be added if desired
                pass

    db.session.commit()
    return sent_list
