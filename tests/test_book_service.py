from app.services.book_service import BookSearchService
import pytest


def test_search_by_isbn_invalid(monkeypatch):
    # invalid ISBN -> None
    monkeypatch.setattr('app.services.book_service.ISBNValidator.is_valid', lambda v: False)
    assert BookSearchService.search_by_isbn('not-an-isbn') is None


def test_search_by_isbn_priority_premium(monkeypatch):
    # premium metadata enabled and returns data -> returned and enhanced with cover
    monkeypatch.setattr('app.services.book_service.ISBNValidator.is_valid', lambda v: True)
    monkeypatch.setattr('app.services.book_service.ISBNValidator.normalize', lambda v: v)

    monkeypatch.setattr('app.services.book_service.PremiumManager.is_enabled', lambda feature: True)

    bn_book = {
        'isbn': '9780000000000',
        'title': 'BN Title',
        'authors': ['Autor X'],
        'cover': None,
        'publisher': 'BN'
    }

    monkeypatch.setattr('app.services.book_service.PremiumManager.call', lambda *a, **k: bn_book)
    monkeypatch.setattr('app.services.book_service.CoverService.get_cover_url', lambda **k: ('http://bn-cover', 'premium_bookcover'))

    res = BookSearchService.search_by_isbn('9780000000000')
    assert res is not None
    assert res['title'] == 'BN Title'
    assert res['cover']['url'] == 'http://bn-cover'
    assert res['cover']['source'] == 'premium_bookcover'


def test_search_by_isbn_fallback_to_openlibrary(monkeypatch):
    # premium disabled -> open library used and cover enhanced
    monkeypatch.setattr('app.services.book_service.ISBNValidator.is_valid', lambda v: True)
    monkeypatch.setattr('app.services.book_service.ISBNValidator.normalize', lambda v: v)

    monkeypatch.setattr('app.services.book_service.PremiumManager.is_enabled', lambda feature: False)

    ol_book = {
        'isbn': '9781111111111',
        'title': 'OL Title',
        'authors': ['Author Y'],
        'cover': None,
        'publisher': 'OL'
    }

    monkeypatch.setattr('app.services.book_service.OpenLibraryClient.search_by_isbn', lambda isbn: ol_book)
    monkeypatch.setattr('app.services.book_service.CoverService.get_cover_url', lambda **k: ('http://ol-cover', 'open_library'))

    res = BookSearchService.search_by_isbn('9781111111111')
    assert res is not None
    assert res['title'] == 'OL Title'
    assert res['cover']['url'] == 'http://ol-cover'
    assert res['cover']['source'] == 'open_library'


def test_search_by_isbn_cover_only_premium(monkeypatch):
    # no metadata anywhere, but premium cover source returns a cover
    monkeypatch.setattr('app.services.book_service.ISBNValidator.is_valid', lambda v: True)
    monkeypatch.setattr('app.services.book_service.ISBNValidator.normalize', lambda v: v)

    monkeypatch.setattr('app.services.book_service.PremiumManager.is_enabled', lambda feature: False)
    monkeypatch.setattr('app.services.book_service.OpenLibraryClient.search_by_isbn', lambda isbn: None)
    monkeypatch.setattr('app.services.book_service.CoverService._get_cover_from_premium_sources', lambda isbn: 'http://premium-cover')

    res = BookSearchService.search_by_isbn('9782222222222')
    assert res is not None
    assert res['source'] == 'premium_cover_only'
    assert res['cover']['url'] == 'http://premium-cover'
    assert res['cover']['source'] == 'premium_bookcover'


def test_search_by_title_short_query_returns_empty(monkeypatch):
    assert BookSearchService.search_by_title('ab') == []


def test_search_by_title_enhances_covers_and_handles_exceptions(monkeypatch):
    # normal enhancement
    ol_results = [
        {'isbn': '9783333333333', 'title': 'T1', 'authors': ['A1']},
        {'isbn': '9784444444444', 'title': 'T2', 'authors': ['A2']}
    ]
    monkeypatch.setattr('app.services.book_service.OpenLibraryClient.search_by_title', lambda title, limit: ol_results)
    monkeypatch.setattr('app.services.book_service.CoverService.get_cover_url', lambda **k: ('http://cover', 'open_library'))

    res = BookSearchService.search_by_title('The Title')
    assert len(res) == 2
    for r in res:
        assert r['cover']['url'] == 'http://cover'
        assert r['cover']['source'] == 'open_library'

    # simulate CoverService failure -> cover set to local_default
    monkeypatch.setattr('app.services.book_service.CoverService.get_cover_url', lambda **k: (_ for _ in ()).throw(Exception('fail')))
    ol_single = [{'isbn': '9785555555555', 'title': 'T3', 'authors': ['A3']}]
    monkeypatch.setattr('app.services.book_service.OpenLibraryClient.search_by_title', lambda title, limit: ol_single)

    res2 = BookSearchService.search_by_title('Another')
    assert len(res2) == 1
    assert res2[0]['cover']['url'] is None
    assert res2[0]['cover']['source'] == 'local_default'


def test__enhance_with_cover_handles_cover_exceptions(monkeypatch):
    book = {'isbn': '9786666666666', 'title': 'Broken', 'authors': ['X']}
    monkeypatch.setattr('app.services.book_service.CoverService.get_cover_url', lambda **k: (_ for _ in ()).throw(Exception('boom')))

    # call the private helper; should not raise and should set local_default
    BookSearchService._enhance_with_cover(book)
    assert book['cover']['url'] is None
    assert book['cover']['source'] == 'local_default'
