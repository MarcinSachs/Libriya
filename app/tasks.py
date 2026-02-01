from datetime import datetime
from app import create_app, db
from app.models import Loan, Notification, User
from app.utils.notifications import create_notification
from flask_babel import _

# This script should be run periodically (e.g. daily) via cron or scheduler


def send_automatic_overdue_notifications():
    app = create_app()
    with app.app_context():
        now = datetime.utcnow()
        overdue_loans = Loan.query.filter_by(status='active').all()
        for loan in overdue_loans:
            if not loan.issue_date or not loan.book or not loan.book.library:
                continue
            overdue_days = loan.book.library.loan_overdue_days or 14
            days_since_issue = (now - loan.issue_date).days
            # Check if already notified
            already_notified = any(n.type == 'overdue_reminder' for n in loan.notifications)
            if days_since_issue > overdue_days and not already_notified:
                message = _(
                    "Reminder: Your loan for \"%(title)s\" is overdue. Please return it as soon as possible.", title=loan.book.title)
                user = User.query.get(loan.user_id)
                create_notification(user, None, message, 'overdue_reminder', loan=loan)
                print(f"Sent overdue reminder for loan {loan.id} to user {user.username}")


if __name__ == "__main__":
    send_automatic_overdue_notifications()
