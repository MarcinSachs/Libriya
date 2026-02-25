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
    # create a small valid PNG image in-memory
    img_buf = io.BytesIO()
    Image.new('RGB', (10, 10), color='red').save(img_buf, format='PNG')
    content = img_buf.getvalue()

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

    # ensure the saved file is a valid image
    img = Image.open(path)
    img.verify()

    # missing extension -> service should determine extension from content (Pillow)
    filename2 = CoverService.download_and_save_cover('http://example.com/pic', upload_folder)
    assert os.path.splitext(filename2)[1].lower() in CoverService.ALLOWED_EXTENSIONS
    img2 = Image.open(os.path.join(upload_folder, filename2))
    img2.verify()

    # too large content-length -> reject
    class BigResp(FakeResp):
        headers = {'content-length': str(CoverService.MAX_COVER_SIZE + 1)}

    monkeypatch.setattr(requests, 'get', lambda *a, **k: BigResp())
    assert CoverService.download_and_save_cover('http://example.com/big.jpg', upload_folder) is None


def test_validate_url_dns_lookup_blocks_private(monkeypatch):
    # simulate DNS resolving to a private IP
    import socket

    def fake_getaddrinfo(hostname, port):
        return [(None, None, None, None, ('10.0.0.1', 0))]

    monkeypatch.setattr(socket, 'getaddrinfo', fake_getaddrinfo)
    assert not CoverService._validate_url('http://internal.example.com/secret')


def test_download_and_save_cover_rejects_non_image(tmp_path, monkeypatch):
    # fake response with non-image bytes
    class FakeResp:
        status_code = 200
        headers = {'content-length': '10'}
        url = 'http://example.com/notimage'

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size=1024):
            yield b'not-an-image'

    monkeypatch.setattr(requests, 'get', lambda *a, **k: FakeResp())
    upload_folder = str(tmp_path)
    assert CoverService.download_and_save_cover('http://example.com/notimage', upload_folder) is None


def test_download_and_save_cover_rejects_redirect_to_private_ip(tmp_path, monkeypatch):
    class RedirectResp:
        status_code = 200
        headers = {'content-length': '10'}
        url = 'http://127.0.0.1/secret'

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size=1024):
            yield b'0' * 10

    monkeypatch.setattr(requests, 'get', lambda *a, **k: RedirectResp())
    assert CoverService.download_and_save_cover('http://example.com/redirect', str(tmp_path)) is None


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


def test_get_cover_url_premium_placeholder_ignored(monkeypatch):
    """If premium returns a 'no-cover' placeholder we should ignore it."""
    class PM:
        @staticmethod
        def is_enabled(feature):
            return True

        @staticmethod
        def call(*a, **k):
            # mimic the problematic CloudFront URL
            return 'https://dryofg8nmyqjw.cloudfront.net/images/no-cover.png'

    monkeypatch.setattr('app.services.premium.manager.PremiumManager', PM)

    # with a valid OL cover available we should get that
    monkeypatch.setattr(CoverService, '_get_cover_from_openlibrary_by_isbn', lambda isbn: 'http://ol/real.jpg')
    url, source = CoverService.get_cover_url(isbn='123')
    assert url == 'http://ol/real.jpg'
    assert source == 'open_library'

    # if OL also fails, fallback to local default
    monkeypatch.setattr(CoverService, '_get_cover_from_openlibrary_by_isbn', lambda isbn: None)
    url2, source2 = CoverService.get_cover_url(isbn='123')
    assert url2 is None and source2 == 'local_default'


def test_get_cover_url_metadata_placeholder_ignored(monkeypatch):
    """If the cover string from metadata is a placeholder, skip it."""
    # disable premium completely
    class PM2:
        @staticmethod
        def is_enabled(feature):
            return False
    monkeypatch.setattr('app.services.premium.manager.PremiumManager', PM2)

    # case 1: OL lookup returns nothing, so we should end up with the local default
    monkeypatch.setattr(CoverService, '_get_cover_from_openlibrary_by_isbn', lambda isbn: None)
    url, source = CoverService.get_cover_url(
        cover_from_source='https://dryofg8nmyqjw.cloudfront.net/images/no-cover.png',
        isbn='xyz'
    )
    assert url is None and source == 'local_default'

    # case 2: OL lookup returns a real cover; placeholder should be ignored
    monkeypatch.setattr(CoverService, '_get_cover_from_openlibrary_by_isbn', lambda isbn: 'http://ol/another.jpg')
    url2, source2 = CoverService.get_cover_url(
        cover_from_source='https://dryofg8nmyqjw.cloudfront.net/images/no-cover.png',
        isbn='xyz'
    )
    assert url2 == 'http://ol/another.jpg'
    assert source2 == 'open_library'


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


def test_validate_url_allows_when_dns_resolution_fails(monkeypatch):
    import socket

    def raise_gai(hostname, port):
        raise socket.gaierror()

    monkeypatch.setattr(socket, 'getaddrinfo', raise_gai)
    # DNS failure should not cause a false positive block for public hostnames
    assert CoverService._validate_url('http://public.example.com/image')


def test_validate_url_rejects_if_any_resolved_ip_is_private(monkeypatch):
    import socket

    def mixed_getaddr(hostname, port):
        return [
            (None, None, None, None, ('203.0.113.5', 0)),
            (None, None, None, None, ('10.1.1.1', 0)),
        ]

    monkeypatch.setattr(socket, 'getaddrinfo', mixed_getaddr)
    # One of the resolved addresses is private -> should be rejected
    assert not CoverService._validate_url('http://mixed.example.com/image')


def test_validate_url_blocks_ipv6_loopback():
    assert not CoverService._validate_url('http://[::1]/secret')
