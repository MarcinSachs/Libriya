import pytest
from app.services.book_service import BookSearchService
from app.services.premium.manager import PremiumManager


def test_search_by_isbn_uses_google_if_bn_empty(monkeypatch, app):
    """When BN returns nothing and google_books is enabled, Google Books should be tried."""
    calls = []

    def fake_isbn(isbn):
        calls.append('bn')
        return None

    def fake_google(isbn):
        calls.append('google')
        return {'title': 'From Google', 'isbn': isbn}

    monkeypatch.setattr(PremiumManager, 'is_enabled', lambda feature: feature in ['biblioteka_narodowa', 'google_books'])
    monkeypatch.setattr(PremiumManager, 'call', lambda feature_id, class_name, method_name, **kwargs: fake_isbn(kwargs['isbn']) if feature_id == 'biblioteka_narodowa' else fake_google(kwargs['isbn']))

    result = BookSearchService.search_by_isbn('9780306406157')
    assert result is not None
    assert result.get('title') == 'From Google'
    assert calls == ['bn', 'google']


def test_search_by_isbn_prefers_bn_over_google(monkeypatch, app):
    """If BN returns data it should be used even if google is enabled."""
    def fake_isbn_bn(isbn):
        return {'title': 'From BN', 'isbn': isbn}

    def fake_isbn_google(isbn):
        pytest.fail("Google Books should not be called when BN returns a result")

    monkeypatch.setattr(PremiumManager, 'is_enabled', lambda feature: True)
    def fake_call(feature_id, class_name, method_name, **kwargs):
        if feature_id == 'biblioteka_narodowa':
            return fake_isbn_bn(kwargs['isbn'])
        if feature_id == 'google_books':
            return fake_isbn_google(kwargs['isbn'])
        return None
    monkeypatch.setattr(PremiumManager, 'call', fake_call)

    res = BookSearchService.search_by_isbn('9780306406157')
    assert res['title'] == 'From BN'
