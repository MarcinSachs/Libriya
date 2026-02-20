import io
import os
import requests
import ipaddress
import pytest
from PIL import Image

from app.services.cover_service import CoverService
from app.services.openlibrary_service import OpenLibraryClient
from app.services import cache_service
from app import db
from app.models import Tenant, Genre, User


def test_validate_url_blocklist_and_schemes():
    # allowed
    assert CoverService._validate_url('http://example.com/image.jpg')
    assert CoverService._validate_url('https://cdn.example.com/1.png')

    # disallowed schemes
    assert not CoverService._validate_url('ftp://example.com/file')

    # localhost / loopback blocked
    assert not CoverService._validate_url('http://localhost/secret')
    assert not CoverService._validate_url('http://127.0.0.1/secret')

    # private IP blocked
    assert not CoverService._validate_url('http://10.0.0.1/image')

    # blocked premium host
    assert not CoverService._validate_url('http://l.longitood.com/cover.jpg')


def test_get_cover_from_openlibrary_by_isbn_parsing(monkeypatch):
    sample_isbn = '9780306406157'

    class DummyResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {f'ISBN:{sample_isbn}': {'cover': {'medium': 'http://ol/med.jpg'}}}

    monkeypatch.setattr(requests, 'get', lambda *a, **k: DummyResp())
    url = CoverService._get_cover_from_openlibrary_by_isbn(sample_isbn)
    assert url == 'http://ol/med.jpg'

    # empty response
    class EmptyResp(DummyResp):
        def json(self):
            return {}

    monkeypatch.setattr(requests, 'get', lambda *a, **k: EmptyResp())
    assert CoverService._get_cover_from_openlibrary_by_isbn(sample_isbn) is None

    # timeout
    monkeypatch.setattr(requests, 'get', lambda *a, **k: (_ for _ in ()).throw(requests.exceptions.Timeout()))
    assert CoverService._get_cover_from_openlibrary_by_isbn(sample_isbn) is None


def test_download_and_save_cover_success_and_extension(tmp_path, monkeypatch):
    content = b'0' * 1024

    class FakeResp:
        status_code = 200
        headers = {'content-length': str(len(content))}

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size=1024):
            yield content

    monkeypatch.setattr(requests, 'get', lambda *a, **k: FakeResp())

    upload_folder = str(tmp_path)
    filename = CoverService.download_and_save_cover('http://example.com/pic.png', upload_folder)
    assert filename is not None
    path = os.path.join(upload_folder, filename)
    assert os.path.exists(path)
    assert os.path.splitext(filename)[1].lower() in CoverService.ALLOWED_EXTENSIONS

    # missing extension defaults to .jpg
    filename2 = CoverService.download_and_save_cover('http://example.com/pic', upload_folder)
    assert filename2.endswith('.jpg')

    # too large content-length -> reject
    class BigResp(FakeResp):
        headers = {'content-length': str(CoverService.MAX_COVER_SIZE + 1)}

    monkeypatch.setattr(requests, 'get', lambda *a, **k: BigResp())
    assert CoverService.download_and_save_cover('http://example.com/big.jpg', upload_folder) is None


def test_get_cover_url_priority_with_premium(monkeypatch):
    # simulate premium manager returning a URL
    class PM:
        @staticmethod
        def is_enabled(feature):
            return True

        @staticmethod
        def call(*a, **k):
            return 'http://premium/cover.jpg'

    monkeypatch.setattr('app.services.premium.manager.PremiumManager', PM)

    url, source = CoverService.get_cover_url(isbn='1')
    assert url == 'http://premium/cover.jpg'
    assert source == 'premium_bookcover'

    # if premium not available, prefer cover_from_source
    class PM2:
        @staticmethod
        def is_enabled(feature):
            return False

    monkeypatch.setattr('app.services.premium.manager.PremiumManager', PM2)
    url2, source2 = CoverService.get_cover_url(cover_from_source='http://ol/cover.png')
    assert url2 == 'http://ol/cover.png' and source2 == 'open_library'


def test_get_cover_url_premium_returns_none_then_fallbacks_to_openlibrary(monkeypatch):
    # Premium feature enabled but PremiumManager.call returns falsy -> fallback to Open Library
    class PM:
        @staticmethod
        def is_enabled(feature):
            return True

        @staticmethod
        def call(*a, **k):
            return None

    monkeypatch.setattr('app.services.premium.manager.PremiumManager', PM)

    # simulate Open Library providing a cover for the ISBN
    monkeypatch.setattr(CoverService, '_get_cover_from_openlibrary_by_isbn', lambda isbn: 'http://ol/fallback.jpg')

    url, source = CoverService.get_cover_url(isbn='999')
    assert url == 'http://ol/fallback.jpg'
    assert source == 'open_library'


def test_get_cover_url_no_sources_uses_local_default(monkeypatch):
    # Premium enabled but no cover, no cover_from_source and no isbn -> local default
    class PM:
        @staticmethod
        def is_enabled(feature):
            return True

        @staticmethod
        def call(*a, **k):
            return None

    monkeypatch.setattr('app.services.premium.manager.PremiumManager', PM)

    url, source = CoverService.get_cover_url()
    assert url is None
    assert source == 'local_default'


def test_cache_service_tenant_and_user_invalidation(app):
    t = Tenant(name='CacheT', subdomain='ctcache')
    db.session.add(t)
    db.session.commit()

    # first fetch - caches value
    first = cache_service.get_tenant_by_id_cached(t.id)
    assert first is not None

    # update name in DB
    t.name = 'CacheT2'
    db.session.commit()

    # cached value remains old until invalidated
    cached = cache_service.get_tenant_by_id_cached(t.id)
    assert cached.name != 'CacheT2'

    # invalidate and check updated
    cache_service.invalidate_tenant_cache(tenant_id=t.id)
    refreshed = cache_service.get_tenant_by_id_cached(t.id)
    assert refreshed.name == 'CacheT2'

    # user cache
    u = User(username='cacheu', email='cu@test.com')
    u.is_email_verified = True
    u.set_password('password')
    db.session.add(u)
    db.session.commit()

    first_u = cache_service.get_user_by_id_cached(u.id)
    assert first_u is not None

    u.username = 'cacheu2'
    db.session.commit()
    still = cache_service.get_user_by_id_cached(u.id)
    assert still.username != 'cacheu2'

    cache_service.invalidate_user_cache(u.id)
    updated = cache_service.get_user_by_id_cached(u.id)
    assert updated.username == 'cacheu2'
