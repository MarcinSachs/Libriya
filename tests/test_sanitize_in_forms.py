from types import SimpleNamespace
from app.forms import RegistrationForm
from app.utils.validators import sanitize_string
from wtforms.validators import ValidationError
from flask import Flask


def test_sanitize_string_basic():
    s = '<b>Bob & Co</b>'
    out = sanitize_string(s, max_length=None)
    assert '&lt;b&gt;Bob &amp; Co&lt;/b&gt;' in out


def test_registration_form_sanitizes_first_and_last():
    # use a minimal Flask app context without initializing the full app fixture
    app = Flask(__name__)
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        form = RegistrationForm()
        # simulate joining existing tenant
        form.create_new_tenant.data = 'false'

        first = SimpleNamespace(data='<script>bad</script>')
        last = SimpleNamespace(data='VeryLongName' * 10)

        # validate should sanitize and not raise required errors
        form.validate_first_name(first)
        assert '&lt;script&gt;bad&lt;/script&gt;' in first.data

        # last name should be truncated to 50 chars
        form.validate_last_name(last)
        assert len(last.data) <= 50


def test_registration_form_required_when_missing():
    app = Flask(__name__)
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        form = RegistrationForm()
        form.create_new_tenant.data = 'false'

        first = SimpleNamespace(data='')
        try:
            form.validate_first_name(first)
            raised = False
        except ValidationError:
            raised = True
        assert raised is True
