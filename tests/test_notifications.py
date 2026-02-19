import pytest
from unittest.mock import MagicMock
from app.utils.notifications import create_notification

class DummyUser:
    def __init__(self, username):
        self.username = username

class DummyLoan:
    pass

class DummyDBSession:
    def __init__(self):
        self.added = []
        self.committed = False
    def add(self, obj):
        self.added.append(obj)
    def commit(self):
        self.committed = True

def test_create_notification_single(monkeypatch):
    dummy_db = DummyDBSession()
    monkeypatch.setattr('app.utils.notifications.db', MagicMock(session=dummy_db))
    monkeypatch.setattr('app.utils.notifications.Notification', MagicMock())
    recipient = DummyUser('user1')
    sender = DummyUser('admin')
    create_notification(recipient, sender, 'msg', 'type')
    assert dummy_db.committed
    assert len(dummy_db.added) == 1

def test_create_notification_multiple(monkeypatch):
    dummy_db = DummyDBSession()
    monkeypatch.setattr('app.utils.notifications.db', MagicMock(session=dummy_db))
    monkeypatch.setattr('app.utils.notifications.Notification', MagicMock())
    recipients = [DummyUser('user1'), DummyUser('user2')]
    sender = DummyUser('admin')
    create_notification(recipients, sender, 'msg', 'type')
    assert dummy_db.committed
    assert len(dummy_db.added) == 2
