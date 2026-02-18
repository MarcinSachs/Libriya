from app.utils.subdomain import slugify_subdomain, is_valid_subdomain


def test_slugify_basic():
    assert slugify_subdomain('Mój Bibliotek') == 'moj-bibliotek'
    assert slugify_subdomain('  Foo!!Bar  ') == 'foo-bar'


def test_slugify_collapse_and_trim():
    assert slugify_subdomain('---Leading--and--Trailing---') == 'leading-and-trailing'
    long = 'A' * 30
    s = slugify_subdomain(long, max_length=20)
    assert len(s) <= 20
    assert s == ('a' * 20)


def test_slugify_empty_and_non_ascii():
    assert slugify_subdomain('') == ''
    assert slugify_subdomain('São Paulo') == 'sao-paulo'


def test_is_valid_subdomain_basic():
    assert is_valid_subdomain('abc')
    assert not is_valid_subdomain('ab')  # too short
    assert not is_valid_subdomain('a' * 21)  # too long
    assert not is_valid_subdomain('-abc')  # starts with hyphen
    assert not is_valid_subdomain('abc-')  # ends with hyphen
    assert not is_valid_subdomain('ab!c')  # invalid char
    assert not is_valid_subdomain('www')  # reserved
    assert is_valid_subdomain('test-1')


def test_slugify_produces_valid_candidate():
    cand = slugify_subdomain('My Library')
    assert cand == 'my-library'
    assert is_valid_subdomain(cand)
