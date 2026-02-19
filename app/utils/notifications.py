from app import db
from app.models import Notification


def create_notification(recipients, sender, message, notification_type, loan=None):
    """
    Create and save notifications for one or multiple recipients.

    Args:
        recipients: User object or list of User objects
        sender: User object (who triggered the notification)
        message: str (notification message)
        notification_type: str (e.g., 'reservation_request', 'loan_approved')
        loan: Loan object (optional, related loan)
    """
    if not isinstance(recipients, list):
        recipients = [recipients]

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
    db.session.commit()
