import re
import pytest

# avoid importing application modules at top-level during pytest discovery because
# the test runner may not set PYTHONPATH correctly; import inside tests instead


def login_user_in_session(client, user):
    """Directly mark a user as logged in by setting session values."""
    with client.session_transaction() as sess:
        sess['user_id'] = user.id
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True
        sess['_id'] = user.get_id() if hasattr(user, 'get_id') else str(user.id)


def test_pwa_settings_in_homepage(client, regular_user):
    # landing page doesn't include PWA configuration; access dashboard instead
    login_user_in_session(client, regular_user)
    res = client.get('/dashboard')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'window.pwaConfig' in html
    assert 'cacheVersion' in html
    assert 'precachePages' in html


def test_service_worker_route(client, regular_user):
    res = client.get('/service-worker.js')
    assert res.status_code == 200
    assert res.headers['Content-Type'] == 'application/javascript'
    body = res.get_data(as_text=True)
    # should contain the cache version from config
    from config import Config
    assert Config().PWA_CACHE_VERSION in body  # new version should appear
    # install listener should define a constant for the cache name
    assert 'PRECACHE_NAME' in body
    assert f"libriya-{Config().PWA_CACHE_VERSION}" in body
    # service-worker content should include workbox import
    assert 'workbox' in body

    # ensure activate event for cleaning old caches is present
    assert 'self.addEventListener' in body and 'activate' in body

    # ensure static assets are also precached by default
    assert '/static/css/style.css' in body
    assert 'pwa-manager.js' in body
    # also ensure a runtime route for /static/ assets exists so offline page is styled
    assert "url.pathname.startsWith('/static/')" in body

    # legacy static path should redirect to new URL
    res2 = client.get('/static/service-worker.js', follow_redirects=False)
    assert res2.status_code in (301, 302)
    assert '/service-worker.js' in res2.headers['Location']


def test_offline_sync_api(client, regular_user):
    # set session directly to bypass login form
    login_user_in_session(client, regular_user)
    payload = {'action_type': 'test', 'payload': {'foo': 'bar'}}
    res = client.post('/api/offline/sync', json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data.get('success') is True


def test_js_module_exports_exist():
    """Ensure that JS files are ES modules and export the expected classes."""
    import pathlib
    base = pathlib.Path(__file__).parents[1] / 'app' / 'static' / 'js'
    pm = (base / 'pwa-manager.js').read_text(encoding='utf-8')
    assert 'export default PWAManager' in pm
    pq = (base / 'pwa-queue.js').read_text(encoding='utf-8')
    assert 'class OfflineQueue' in pq


def test_service_worker_precache_only_public(client):
    # The service worker should filter the list of URLs it actually precaches.
    res = client.get('/service-worker.js')
    assert res.status_code == 200
    body = res.get_data(as_text=True)
    # after filtering only '/' and '/offline' should remain
    assert "filter(u => u === '/' || u === '/offline')" in body
    # offline page should still be mentioned in the precache map call later on
    assert '/offline' in body


def test_offline_page_content(client):
    res = client.get('/offline')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    # must not include CDN references (old, now removed)
    assert 'cdn.tailwindcss' not in html
    assert 'boxicons' not in html
    # color scheme enforced as light, styles should include !important
    assert 'color-scheme' in html
    assert 'background: #fff !important' in html
    assert 'color: #000 !important' in html
    # content is minimal (no big layout divs)
    assert '<div class="bg-white' not in html
    assert '<h1' in html and 'You are offline' in html


def test_offline_page_minimal(client):
    res = client.get('/offline')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    # minimal content should be present and not include big layout markers
    assert '<h1' in html and 'You are offline' in html
    # no tailwind CDN or external CSS references
    assert 'cdn.tailwindcss' not in html
    # page should be self-contained and not include external resources
    assert '<script' not in html


def test_session_cookie_configuration(client):
    # the default development environment must avoid `Secure` cookies so the
    # browser actually sends them over plain HTTP.  The test client inherits
    # this value from the application config.
    assert client.application.config['SESSION_COOKIE_SECURE'] is False


def test_cached_manager_user_can_access_libraries(client, manager_user):
    """Ensure a cached user instance is merged back into the session.

    We prime the cache by visiting ``/libraries/`` once, then explicitly
    expunge the session objects to simulate the detached-instance scenario the
    development log showed.  A second request must still return 200 instead of
    raising DetachedInstanceError.
    """
    login_user_in_session(client, manager_user)
    # first request warms the cache and updates relationship data
    res1 = client.get('/libraries/')
    assert res1.status_code == 200

    # clear the SQLAlchemy session to detach everything
    with client.application.app_context():
        from app import db
        db.session.expunge_all()

    # second request should still succeed thanks to merging in user_loader
    res2 = client.get('/libraries/')
    assert res2.status_code == 200


def test_login_persists_across_requests(client, regular_user):
    # ensure the session established by `login_user_in_session` is honored on
    # subsequent navigation (simulates a page refresh).  '/dashboard' is a
    # simple authenticated endpoint available to all users.
    login_user_in_session(client, regular_user)
    res = client.get('/dashboard')
    assert res.status_code == 200, 'first request should show dashboard'
    # repeat the request to simulate a refresh/navigation
    res2 = client.get('/dashboard')
    assert res2.status_code == 200


def test_offline_sync_formats(client, regular_user):
    # login first
    login_user_in_session(client, regular_user)

    # old-style action
    res = client.post('/api/offline/sync', json={'action_type': 'foo', 'payload': {'x': 1}})
    assert res.status_code == 200
    assert res.get_json().get('success') is True

    # new-style request data
    req = {'url': '/test-url', 'options': {'method': 'POST', 'body': 'hello'}}
    res2 = client.post('/api/offline/sync', json=req)
    assert res2.status_code == 200
    assert res2.get_json().get('note') == 'received new-style request'
