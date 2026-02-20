import pytest
import requests
from datetime import datetime

from app.services.openlibrary_service import OpenLibraryClient
from app import db
from app.models import Genre


def test_get_cover_url():
    url = OpenLibraryClient.get_cover_url(12345, size='L')
    assert url.endswith('/id/12345-L.jpg')


def test_map_ol_subjects_to_genres_exact_and_partial():
    subjects = ['Science Fiction', 'mystery, thriller', 'graphic novel']
    mapped = OpenLibraryClient.map_ol_subjects_to_genres(subjects)
    # Expect mapped genre names (sorted)
    assert 'Fiction' in mapped or 'Science Fiction' in mapped
    assert 'Crime / Thriller' in mapped
    assert 'Comic' in mapped

    # compound subject splitting and partial match
    subjects2 = ['historical fiction, romance']
    mapped2 = OpenLibraryClient.map_ol_subjects_to_genres(subjects2)
    assert 'Fiction' in mapped2 and 'Romance / Contemporary' in mapped2


def test_search_by_isbn_parsing_and_errors(monkeypatch):
    sample_isbn = '9780306406157'

    class DummyResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                f'ISBN:{sample_isbn}': {
                    'title': 'Sample Title',
                    'authors': [{'name': 'A. Author'}],
                    'publish_date': '1999',
                    'cover': {'large': 'http://cover.example/large.jpg'},
                    'publishers': [{'name': 'PubHouse'}],
                    'subjects': ['Fiction', 'Mystery'],
                    'description': {'value': 'A description'},
                    'languages': [{'key': '/languages/eng'}],
                    'number_of_pages': 250,
                    'key': '/books/OL123M'
                }
            }

    monkeypatch.setattr(requests, 'get', lambda *a, **k: DummyResp())

    result = OpenLibraryClient.search_by_isbn(sample_isbn)
    assert result is not None
    assert result['title'] == 'Sample Title'
    assert result['authors'] == ['A. Author']
    assert result['year'] == 1999
    assert result['isbn'] == sample_isbn
    assert result['publisher'] == 'PubHouse'
    assert result['cover'].startswith('http')

    # when API returns empty dict -> None
    class EmptyResp(DummyResp):
        def json(self):
            return {}

    monkeypatch.setattr(requests, 'get', lambda *a, **k: EmptyResp())
    assert OpenLibraryClient.search_by_isbn(sample_isbn) is None

    # simulate timeout
    def raise_timeout(*a, **k):
        raise requests.exceptions.Timeout()

    monkeypatch.setattr(requests, 'get', raise_timeout)
    assert OpenLibraryClient.search_by_isbn(sample_isbn) is None


def test_search_by_title_and_limit_and_timeout(monkeypatch):
    # short query returns [] immediately
    assert OpenLibraryClient.search_by_title('ab') == []

    # simulate normal search response
    class SR:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                'docs': [
                    {'title': 'T1', 'author_name': ['A1'], 'first_publish_year': 2001, 'isbn': ['111'], 'cover_i': 10},
                    {'title': 'T2', 'author_name': ['A2'], 'first_publish_year': 2002, 'isbn': [], 'cover_i': 20},
                    {'title': 'T3', 'author_name': ['A3'], 'first_publish_year': 2003, 'isbn': ['333'], 'cover_i': None},
                ]
            }

    monkeypatch.setattr(requests, 'get', lambda *a, **k: SR())
    res = OpenLibraryClient.search_by_title('testing', limit=5)
    # only docs with isbn should be returned
    assert isinstance(res, list)
    assert len(res) == 2
    assert res[0]['isbn'] == '111'
    assert res[1]['isbn'] == '333'

    # simulate timeout
    monkeypatch.setattr(requests, 'get', lambda *a, **k: (_ for _ in ()).throw(requests.exceptions.Timeout()))
    assert OpenLibraryClient.search_by_title('testing') == []


def test_get_genre_ids_for_subjects_db_integration(app):
    # create genres expected by mapping
    g1 = Genre(name='Fiction')
    g2 = Genre(name='Crime / Thriller')
    db.session.add_all([g1, g2])
    db.session.commit()

    subjects = ['historical fiction, mystery']
    ids = OpenLibraryClient.get_genre_ids_for_subjects(subjects)

    # both genre ids should be present (order not guaranteed)
    assert set(ids) == set([g1.id, g2.id])


def test_parse_book_data_description_and_year_parsing(monkeypatch):
    isbn = '9999999999'

    class R:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                f'ISBN:{isbn}': {
                    'title': 'Edge Case',
                    'authors': [{'name': 'Edge Author'}],
                    'publish_date': 'June 5, 2005',
                    'cover': {'medium': 'http://cover.example/med.jpg'},
                    'publishers': ['PubStr'],
                    'subjects': [{'name': 'Science'}],
                    'description': 'Short desc',
                    'languages': [],
                    'number_of_pages': None,
                    'key': '/books/OL999M'
                }
            }

    monkeypatch.setattr(requests, 'get', lambda *a, **k: R())
    parsed = OpenLibraryClient.search_by_isbn(isbn)
    assert parsed is not None
    assert parsed['year'] == 2005
    assert parsed['description'] == 'Short desc'
    # medium cover should be picked
    assert parsed['cover'] and 'med.jpg' in parsed['cover']


def test_map_ol_subjects_to_genres_handles_empty_and_duplicates():
    subjects = ['', 'fiction, fiction']
    mapped = OpenLibraryClient.map_ol_subjects_to_genres(subjects)
    assert mapped == ['Fiction']


def test_search_by_title_limit_capped_and_missing_fields(monkeypatch):
    # create 25 docs all with ISBNs (to test cap at 20)
    docs = []
    for i in range(25):
        # vary presence of author/year
        doc = {'title': f'T{i}', 'isbn': [f'IS{i}']}
        if i % 2 == 0:
            doc['author_name'] = [f'A{i}']
        if i % 3 == 0:
            doc['first_publish_year'] = 2000 + i
        docs.append(doc)

    class SR2:
        def raise_for_status(self):
            return None

        def json(self):
            return {'docs': docs}

    monkeypatch.setattr(requests, 'get', lambda *a, **k: SR2())

    res = OpenLibraryClient.search_by_title('longquery', limit=50)
    # capped at 20
    assert len(res) == 20
    # documents with missing author -> authors list should be present (possibly empty)
    assert isinstance(res[1].get('authors', []), list)
    # documents with missing year -> year may be None
    assert 'year' in res[2]


def test_get_genre_ids_for_subjects_no_match_returns_empty(app):
    ids = OpenLibraryClient.get_genre_ids_for_subjects(['unmapped-subject-xyz'])
    assert ids == []
