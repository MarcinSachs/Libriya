import pytest
from app.services.book_service import BookSearchService
from app.services.premium.manager import PremiumManager
from app.services.openlibrary_service import OpenLibraryClient


def test_search_by_isbn_uses_google_if_bn_empty(monkeypatch, app):
    """When BN returns nothing and google_books is enabled, Google Books should be tried."""
    calls = []

    def fake_isbn(isbn):
        calls.append('bn')
        return None

    def fake_google(isbn):
        calls.append('google')
        # return an author so we can assert formatting
        return {'title': 'From Google', 'isbn': isbn, 'authors': ['Jane Roe']}

    monkeypatch.setattr(PremiumManager, 'is_enabled', lambda feature: feature in [
                        'biblioteka_narodowa', 'google_books'])
    monkeypatch.setattr(PremiumManager, 'call', lambda feature_id, class_name, method_name, **
                        kwargs: fake_isbn(kwargs['isbn']) if feature_id == 'biblioteka_narodowa' else fake_google(kwargs['isbn']))

    result = BookSearchService.search_by_isbn('9780306406157')
    assert result is not None
    assert result.get('title') == 'From Google'
    # authors should be reformatted by the service helper
    assert result.get('authors') == ['Roe Jane']
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


def test_search_by_title_fallback_to_google(monkeypatch, app):
    """When Open Library yields no titles, Google Books should be tried if enabled."""
    calls = []

    def fake_ol(query, limit):
        calls.append('ol')
        return []

    def fake_gb(title, author=None, limit=10):
        calls.append('google')
        return [{'title': 'GB Book', 'isbn': '12345'}]

    monkeypatch.setattr(OpenLibraryClient, 'search_by_title', fake_ol)
    monkeypatch.setattr(PremiumManager, 'is_enabled', lambda f: f == 'google_books' or f == 'biblioteka_narodowa')
    monkeypatch.setattr(PremiumManager, 'call', lambda feature_id, class_name, method_name, **
                        kwargs: fake_gb(**kwargs) if feature_id == 'google_books' else None)

    results = BookSearchService.search_by_title('some title')
    assert len(results) == 1
    assert results[0]['title'] == 'GB Book'
    assert calls == ['ol', 'google']


def test_search_by_title_prefers_ol_over_google(monkeypatch, app):
    """If OL returns something, Google Books must not be called."""
    def fake_ol(query, limit):
        return [{'title': 'OL Book', 'isbn': '9876'}]

    def fake_gb(title, author=None, limit=10):
        pytest.fail('Google Books should not be used when OL returns data')

    monkeypatch.setattr(OpenLibraryClient, 'search_by_title', fake_ol)
    monkeypatch.setattr(PremiumManager, 'is_enabled', lambda f: True)
    monkeypatch.setattr(PremiumManager, 'call', lambda *args, **kwargs: fake_gb(**kwargs))

    res = BookSearchService.search_by_title('xxx')
    assert res[0]['title'] == 'OL Book'
