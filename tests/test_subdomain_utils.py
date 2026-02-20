from app.utils.subdomain import slugify_subdomain, is_valid_subdomain, unique_candidate
import re


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


def test_is_valid_subdomain_edges_and_cases():
    # boundary lengths
    assert is_valid_subdomain('a' * 3)
    assert is_valid_subdomain('a' * 20)

    # uppercase is not valid
    assert not is_valid_subdomain('Abc')

    # multiple hyphens inside are allowed
    assert is_valid_subdomain('a--b')


def test_unique_candidate_basic_and_numeric_suffix():
    exists = lambda s: False
    assert unique_candidate('My Library', exists) == 'my-library'

    taken = {'library'}
    exists2 = lambda s: s in taken
    assert unique_candidate('library', exists2) == 'library-1'


def test_unique_candidate_truncation_and_suffix_length():
    # base is full-length; numeric suffix should cause truncation to fit
    base = 'a' * 20
    taken = {base}
    exists = lambda s: s in taken
    cand = unique_candidate(base, exists)
    assert cand.endswith('-1')
    assert len(cand) <= 20
    assert cand == ('a' * 18) + '-1'


def test_unique_candidate_fallback_random_token():
    base = 'taken'
    # mark base and all numeric suffixes as taken to force fallback
    taken = {base} | {f"{base}-{i}" for i in range(1, 1000)}
    exists = lambda s: s in taken

    cand = unique_candidate(base, exists)
    # should be base-<6 hex chars>
    assert re.match(rf'^{base}-[0-9a-f]{{6}}$', cand)
    assert len(cand) <= 20


def test_unique_candidate_empty_and_short_base():
    exists = lambda s: False
    # empty base -> 'tenant'
    assert unique_candidate('', exists) == 'tenant'

    # too-short base should get a numeric suffix
    assert unique_candidate('ab', exists) == 'ab-1'


def test_unique_candidate_reserved_base_is_handled():
    exists = lambda s: False
    # 'www' is reserved so should produce 'www-1'
    assert unique_candidate('www', exists) == 'www-1'
