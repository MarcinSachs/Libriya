import pytest
from app import db
from app.models import User, Tenant, Library, Genre, Book, Comment
import os
import io
from PIL import Image


def login(client, username, password='password'):
    return client.post('/auth/login/', data={'email_or_username': username, 'password': password}, follow_redirects=True)


def test_api_genres_from_isbn_test_endpoint(client):
    res = client.post('/api/book/genres-from-isbn/test', json={'isbn': '9780306406157'})
    assert res.status_code == 200
    data = res.get_json()
    assert data.get('success') is True
    assert data.get('isbn') == '9780306406157'


def test_api_genres_from_isbn_with_premium(monkeypatch, client, app):
    """Real endpoint should call PremiumManager with the correct signature and map genres."""
    # create a matching genre so mapping works
    g = Genre(name='Fiction')
    db.session.add(g)
    db.session.commit()

    def fake_call(feature_id, class_name, method_name, **kwargs):
        # verify parameters passed correctly
        assert feature_id == 'biblioteka_narodowa'
        assert class_name == 'BibliotekaNarodowaService'
        assert method_name == 'search_by_isbn'
        assert kwargs.get('isbn') == '12345'
        return {'genres': ['Fiction']}

    monkeypatch.setattr('app.routes.books.PremiumManager.call', fake_call)
    res = client.post('/api/book/genres-from-isbn', json={'isbn': '12345'})
    assert res.status_code == 200
    data = res.get_json()
    assert data['genres'] == [{'id': g.id, 'name': g.name}]


def test_book_add_post_as_admin(app, client, monkeypatch):
    # prepare tenant, library, genre and admin user
    t = Tenant(name='Tbook', subdomain='tb')
    db.session.add(t)
    db.session.commit()

    lib = Library(name='LibBook', tenant_id=t.id)
    db.session.add(lib)
    db.session.commit()

    g = Genre(name='Fiction')
    db.session.add(g)
    db.session.commit()

    admin = User(username='admin1', email='a1@example.com', role='admin', tenant_id=t.id)
    admin.is_email_verified = True
    admin.set_password('password')
    db.session.add(admin)
    db.session.commit()

    # login as admin
    rv = login(client, admin.email)
    assert b'Please log in' not in rv.data

    # GET form
    get = client.get('/books/add/')
    assert get.status_code == 200

    # POST add book
    # now test that PremiumManager is invoked when description is empty
    called = {'flag': False}

    def fake_premium(feature_id, class_name, method_name, **kwargs):
        called['flag'] = True
        assert feature_id == 'biblioteka_narodowa'
        assert class_name == 'BibliotekaNarodowaService'
        assert method_name == 'search_by_isbn'
        assert kwargs.get('isbn') == '9780306406157'
        return {'description': 'Generated description from premium'}

    monkeypatch.setattr('app.routes.books.PremiumManager.call', fake_premium)

    post_data = {
        'isbn': '9780306406157',
        'title': 'New Book',
        'author': 'Author One',
        'library': lib.id,
        'genres': [str(g.id)],
        'year': 2000,
        'description': ''
    }
    post = client.post('/books/add/', data=post_data, follow_redirects=True)
    assert post.status_code == 200

    b = Book.query.filter_by(title='New Book').first()
    assert b is not None
    assert b.library_id == lib.id
    assert any(ge.name == 'Fiction' for ge in b.genres)
    assert b.description == 'Generated description from premium'
    assert called['flag'] is True


def test_book_delete_and_manager_permissions(app, client):
    # setup tenant, two libraries and users
    t = Tenant(name='TD', subdomain='td')
    db.session.add(t)
    db.session.commit()

    lib1 = Library(name='L1', tenant_id=t.id)
    lib2 = Library(name='L2', tenant_id=t.id)
    db.session.add_all([lib1, lib2])
    db.session.commit()

    manager = User(username='mgr', email='mgr@example.com', role='manager', tenant_id=t.id)
    manager.is_email_verified = True
    manager.set_password('password')
    manager.libraries.append(lib1)

    admin = User(username='adm2', email='adm2@example.com', role='admin', tenant_id=t.id)
    admin.is_email_verified = True
    admin.set_password('password')

    db.session.add_all([manager, admin])
    db.session.commit()

    # book in lib2 (manager does NOT manage lib2)
    book = Book(title='ToBeDeleted', library_id=lib2.id, tenant_id=t.id, year=2010)
    db.session.add(book)
    db.session.commit()

    # manager cannot delete book in other library
    login(client, manager.email)
    resp = client.post(f'/book_delete/{book.id}', data={'csrf_token': ''}, follow_redirects=True)
    assert resp.status_code == 200
    # book still exists
    assert Book.query.get(book.id) is not None

    # admin can delete
    login(client, admin.email)
    resp2 = client.post(f'/book_delete/{book.id}', data={'csrf_token': ''}, follow_redirects=True)
    assert resp2.status_code == 200
    assert Book.query.get(book.id) is None

    # create unavailable book -> cannot delete
    b2 = Book(title='OnLoan', library_id=lib1.id, tenant_id=t.id, year=2011, status='on_loan')
    db.session.add(b2)
    db.session.commit()

    login(client, admin.email)
    resp3 = client.post(f'/book_delete/{b2.id}', data={'csrf_token': ''}, follow_redirects=True)
    assert resp3.status_code == 200
    assert Book.query.get(b2.id) is not None


def test_book_detail_comment_posting(app, client):
    t = Tenant(name='TC', subdomain='tc')
    db.session.add(t)
    db.session.commit()

    lib = Library(name='LC', tenant_id=t.id)
    db.session.add(lib)
    db.session.commit()

    user = User(username='u_c', email='uc@example.com', tenant_id=t.id)
    user.is_email_verified = True
    user.set_password('password')
    db.session.add(user)
    db.session.commit()

    book = Book(title='CommentBook', library_id=lib.id, tenant_id=t.id, year=2022)
    db.session.add(book)
    db.session.commit()

    login(client, user.email)
    res = client.post(f'/book/{book.id}', data={'text': 'A nice comment'}, follow_redirects=True)
    assert res.status_code == 200

    comment = Comment.query.filter_by(book_id=book.id, user_id=user.id).first()
    assert comment is not None
    assert 'nice comment' in comment.text.lower()


def test_cleanup_cover_filename_validation_and_deletion(app, client):
    # login a test user (endpoint requires authentication)
    u = User(username='cleanup_user', email='cu@example.com')
    u.is_email_verified = True
    u.set_password('password')
    db.session.add(u)
    db.session.commit()
    login(client, u.email)

    # invalid filename (contains disallowed char)
    res = client.post('/api/cleanup-cover', json={'cover_url': 'bad|name.jpg'})
    assert res.status_code == 400
    data = res.get_json()
    assert data['success'] is False

    # missing cover_url
    res2 = client.post('/api/cleanup-cover', json={})
    assert res2.status_code == 400

    # create a file inside upload folder and delete it via API
    folder = app.config['UPLOAD_FOLDER']
    os.makedirs(folder, exist_ok=True)
    filename = 'to_delete.jpg'
    path = os.path.join(folder, filename)

    # create a small valid image
    img = Image.new('RGB', (10, 10), color=(73, 109, 137))
    img.save(path, 'JPEG')
    assert os.path.exists(path)

    res3 = client.post('/api/cleanup-cover', json={'cover_url': f'/static/uploads/{filename}'})
    assert res3.status_code == 200
    data3 = res3.get_json()
    assert data3.get('success') is True
    assert not os.path.exists(path)


def test_book_add_page_js_contains_preview_and_cleanup_logic(client, app):
    """Ensure the add-book page includes updated JS for cover preview and unload cleanup."""
    # prepare minimal user and login
    t = Tenant(name='JsTest', subdomain='jt')
    db.session.add(t)
    db.session.commit()
    u = User(username='jsuser', email='js@example.com', tenant_id=t.id, role='admin')
    u.is_email_verified = True
    u.set_password('password')
    db.session.add(u)
    db.session.commit()
    login(client, u.email)

    res = client.get('/books/add/')
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # the JS should treat both http and /static URLs as direct images
    assert "book.cover_id.startsWith('http') || book.cover_id.startsWith('/')" in html
    # the beforeunload cleanup code should be present
    assert 'window.addEventListener' in html and 'beforeunload' in html
    assert '/api/cleanup-cover' in html
    # file input preview code added in macros
    assert 'FileReader' in html
    # handleCancel now strips query strings and logs
    assert 'coverUrl = coverUrl.split' in html
    assert "console.log('[Cancel]" in html


def test_cleanup_cover_accepts_query_string(client, app):
    # verify server will delete file even if URL includes a cache-busting query
    u = User(username='cleanup_user2', email='cu2@example.com')
    u.is_email_verified = True
    u.set_password('password')
    db.session.add(u)
    db.session.commit()
    login(client, u.email)

    folder = app.config['UPLOAD_FOLDER']
    os.makedirs(folder, exist_ok=True)
    filename = 'query.jpg'
    path = os.path.join(folder, filename)
    from PIL import Image
    Image.new('RGB', (5, 5)).save(path)
    assert os.path.exists(path)

    # send with query string appended
    res = client.post('/api/cleanup-cover', json={'cover_url': f'/static/uploads/{filename}?v=1'})
    assert res.status_code == 200
    data = res.get_json()
    assert data.get('success') is True
    assert not os.path.exists(path)

    # create another file and simulate a beacon-like non-JSON call
    filename2 = 'plain.jpg'
    path2 = os.path.join(folder, filename2)
    Image.new('RGB', (5, 5)).save(path2)
    assert os.path.exists(path2)

    res2 = client.post('/api/cleanup-cover', data=f'/static/uploads/{filename2}', content_type='text/plain')
    assert res2.status_code == 200
    data2 = res2.get_json()
    assert data2.get('success') is True
    # file should remain because we didn't actually tell it what to delete
    assert os.path.exists(path2)
    # manually remove
    os.remove(path2)


def test_cover_thumbnail_and_micro_endpoints(app, client):
    # setup tenant, library, user and book with cover file
    t = Tenant(name='ThumbTenant', subdomain='tt')
    db.session.add(t)
    db.session.commit()

    lib = Library(name='ThumbLib', tenant_id=t.id)
    db.session.add(lib)
    db.session.commit()

    user = User(username='thumbu', email='thumb@example.com', tenant_id=t.id)
    user.is_email_verified = True
    user.set_password('password')
    db.session.add(user)
    db.session.commit()

    # prepare cover file
    folder = app.config['UPLOAD_FOLDER']
    os.makedirs(folder, exist_ok=True)
    cover_name = 'thumb_test.jpg'
    cover_path = os.path.join(folder, cover_name)
    img = Image.new('RGB', (400, 600), color=(255, 0, 0))
    img.save(cover_path, 'JPEG')

    book = Book(title='ThumbBook', library_id=lib.id, tenant_id=t.id, year=2020, cover=cover_name)
    db.session.add(book)
    db.session.commit()

    # thumbnail endpoint
    resp = client.get(f'/api/books/{book.id}/cover/thumbnail')
    assert resp.status_code == 200
    assert resp.headers['Content-Type'] == 'image/jpeg'

    # micro endpoint
    resp2 = client.get(f'/api/books/{book.id}/cover/micro')
    assert resp2.status_code == 200
    assert resp2.headers['Content-Type'] == 'image/jpeg'

    # missing cover returns 404
    book2 = Book(title='NoCover', library_id=lib.id, tenant_id=t.id, year=2021)
    db.session.add(book2)
    db.session.commit()

    resp3 = client.get(f'/api/books/{book2.id}/cover/thumbnail')
    assert resp3.status_code == 404
    resp4 = client.get(f'/api/books/{book2.id}/cover/micro')
    assert resp4.status_code == 404

    # cleanup
    try:
        os.remove(cover_path)
    except Exception:
        pass
