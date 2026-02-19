import pytest
from unittest.mock import patch, MagicMock
from app.services.openlibrary_service import OpenLibraryClient

@patch('app.services.openlibrary_service.requests.get')
def test_search_by_isbn_success(mock_get):
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

@patch('app.services.openlibrary_service.requests.get')
def test_search_by_title_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        'docs': [
            {'title': 'Book1', 'author_name': ['A'], 'first_publish_year': 2000, 'isbn': ['123']},
            {'title': 'Book2', 'author_name': ['B'], 'first_publish_year': 2001, 'isbn': ['456']}
        ]
    }
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp
    results = OpenLibraryClient.search_by_title('Book')
    assert len(results) == 2
    assert results[0]['title'] == 'Book1'
    assert results[1]['title'] == 'Book2'
