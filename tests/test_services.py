import pytest
from unittest.mock import patch, MagicMock
from app.services.book_service import BookSearchService
from app.services.openlibrary_service import OpenLibraryClient
from app.services.isbn_validator import ISBNValidator
from app.services.cover_service import CoverService

@patch('app.services.book_service.ISBNValidator')
@patch('app.services.book_service.PremiumManager')
@patch('app.services.book_service.OpenLibraryClient')
@patch('app.services.book_service.CoverService')
def test_book_search_service_search_by_isbn(mock_cover, mock_ol, mock_pm, mock_isbn):
    mock_isbn.is_valid.return_value = True
    mock_isbn.normalize.return_value = '9780545003957'
    mock_pm.is_enabled.return_value = True
    mock_pm.call.return_value = {'title': 'BN Book', 'cover': None, 'authors': ['A'], 'isbn': '9780545003957'}
    mock_cover.get_cover_url.return_value = ('cover_url', 'premium_bookcover')
    result = BookSearchService.search_by_isbn('9780545003957')
    assert result['title'] == 'BN Book'
    assert result['cover']['url'] == 'cover_url'
    mock_pm.call.return_value = None
    mock_ol.search_by_isbn.return_value = {'title': 'OL Book', 'cover': None, 'authors': ['B'], 'isbn': '9780545003957'}
    result = BookSearchService.search_by_isbn('9780545003957')
    assert result['title'] == 'OL Book'
    mock_ol.search_by_isbn.return_value = None
    mock_cover._get_cover_from_premium_sources.return_value = 'premium_url'
    result = BookSearchService.search_by_isbn('9780545003957')
    assert result['cover']['url'] == 'premium_url'
    mock_cover._get_cover_from_premium_sources.return_value = None
    result = BookSearchService.search_by_isbn('9780545003957')
    assert result is None

def test_isbn_validator():
    assert ISBNValidator.is_valid('9780545003957')
    assert not ISBNValidator.is_valid('badisbn')
    assert ISBNValidator.normalize('978-0-545-00395-7') == '9780545003957'
    assert ISBNValidator.format_isbn_13('048665088X').startswith('978-0-486-65088')

@patch('app.services.openlibrary_service.requests.get')
def test_openlibraryclient_search_by_isbn(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        'ISBN:9780545003957': {
            'title': 'Test Book',
            'authors': [{'name': 'Author'}],
            'publish_date': '2007',
            'cover': {'large': 'url'},
            'publishers': ['Publisher'],
            'subjects': ['fiction']
        }
    }
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp
    result = OpenLibraryClient.search_by_isbn('9780545003957')
    assert result['title'] == 'Test Book'
    assert 'Author' in result['authors']
    assert result['year'] == 2007 or result['year'] == '2007'

@patch('app.services.cover_service.CoverService._get_cover_from_premium_sources')
def test_cover_service_get_cover_url(mock_premium):
    mock_premium.return_value = 'http://premium.cover/url.jpg'
    url, source = CoverService.get_cover_url(isbn='9780545003957')
    assert url == 'http://premium.cover/url.jpg'
    assert source == 'premium_bookcover'
