from app.utils.password_validator import is_strong_password, check_pwned_password


def test_is_strong_password_ok():
    ok, reasons = is_strong_password('Str0ng!Passw0rd')
    assert ok
    assert reasons == []


def test_is_strong_password_fail():
    ok, reasons = is_strong_password('weak')
    assert not ok
    assert any('at least 12' in r or 'uppercase' in r.lower() for r in reasons)

# Note: check_pwned_password hits external API; avoid running in unit tests by default.
