import pytest
from unittest.mock import patch, MagicMock
from app.services.book_service import BookSearchService

@patch('app.services.book_service.ISBNValidator')
@patch('app.services.book_service.PremiumManager')
@patch('app.services.book_service.OpenLibraryClient')
@patch('app.services.book_service.CoverService')
def test_search_by_isbn_priority(mock_cover, mock_ol, mock_pm, mock_isbn):
    # Valid ISBN
    mock_isbn.is_valid.return_value = True
    mock_isbn.normalize.return_value = '9780545003957'
    # Premium enabled, BN returns data
    mock_pm.is_enabled.return_value = True
    mock_pm.call.return_value = {'title': 'BN Book', 'cover': None, 'authors': ['A'], 'isbn': '9780545003957'}
    mock_cover.get_cover_url.return_value = ('cover_url', 'premium_bookcover')
    result = BookSearchService.search_by_isbn('9780545003957')
    assert result['title'] == 'BN Book'
    assert result['cover']['url'] == 'cover_url'
    # Premium enabled, BN returns None, OL returns data
    mock_pm.call.return_value = None
    mock_ol.search_by_isbn.return_value = {'title': 'OL Book', 'cover': None, 'authors': ['B'], 'isbn': '9780545003957'}
    result = BookSearchService.search_by_isbn('9780545003957')
    assert result['title'] == 'OL Book'
    # Both BN and OL return None, premium cover found
    mock_ol.search_by_isbn.return_value = None
    mock_cover._get_cover_from_premium_sources.return_value = 'premium_url'
    result = BookSearchService.search_by_isbn('9780545003957')
    assert result['cover']['url'] == 'premium_url'
    # All sources return None
    mock_cover._get_cover_from_premium_sources.return_value = None
    result = BookSearchService.search_by_isbn('9780545003957')
    assert result is None

def test_search_by_isbn_invalid():
    with patch('app.services.book_service.ISBNValidator') as mock_isbn:
        mock_isbn.is_valid.return_value = False
        result = BookSearchService.search_by_isbn('badisbn')
        assert result is None
