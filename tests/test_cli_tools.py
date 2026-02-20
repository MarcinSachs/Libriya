from datetime import datetime, timedelta
from app import db
from app.models import Notification, User


def test_cleanup_notifications_deletes_old_read_notifications(app, runner):
    with app.app_context():
        # create notifications with varying timestamps and read flags
        old_read = Notification(recipient_id=1, sender_id=None, message='old read', type='info', is_read=True,
                                timestamp=datetime.utcnow() - timedelta(days=31))
        recent_read = Notification(recipient_id=1, sender_id=None, message='recent read', type='info', is_read=True,
                                   timestamp=datetime.utcnow() - timedelta(days=5))
        old_unread = Notification(recipient_id=1, sender_id=None, message='old unread', type='info', is_read=False,
                                  timestamp=datetime.utcnow() - timedelta(days=40))

        db.session.add_all([old_read, recent_read, old_unread])
        db.session.commit()

        # Run CLI (default days=30) -> should delete only old_read
        result = runner.invoke(args=['cleanup-notifications'])
        assert 'Deleted 1 old notifications' in result.output

        remaining = Notification.query.all()
        messages = [n.message for n in remaining]
        assert 'recent read' in messages
        assert 'old unread' in messages
        assert 'old read' not in messages


def test_cleanup_notifications_respects_days_option(app, runner):
    with app.app_context():
        # create a read notification 2 days old
        n = Notification(recipient_id=1, sender_id=None, message='two days old', type='info', is_read=True,
                         timestamp=datetime.utcnow() - timedelta(days=2))
        db.session.add(n)
        db.session.commit()

        # days=1 -> should delete (2 days old > 1)
        res1 = runner.invoke(args=['cleanup-notifications', '--days', '1'])
        assert 'Deleted 1 old notifications' in res1.output
        assert Notification.query.filter_by(message='two days old').first() is None

        # days=2 -> no further deletions (already removed)
        res2 = runner.invoke(args=['cleanup-notifications', '--days', '2'])
        assert 'Deleted 0 old notifications' in res2.output
        assert Notification.query.filter_by(message='two days old').first() is None