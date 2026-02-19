import pytest
from app.utils.subdomain import slugify_subdomain, is_valid_subdomain

def test_slugify_subdomain():
    assert slugify_subdomain('Test Subdomain!') == 'test-subdomain'
    assert slugify_subdomain('Zażółć gęślą jaźń') == 'zazoc-gesla-jazn'
    assert slugify_subdomain('A'*30) == 'a'*20
    assert slugify_subdomain('---foo---bar---') == 'foo-bar'
    assert slugify_subdomain('') == ''

def test_is_valid_subdomain():
    assert is_valid_subdomain('abc')
    assert is_valid_subdomain('foo-bar')
    assert not is_valid_subdomain('ab')  # too short
    assert not is_valid_subdomain('a'*21)  # too long
    assert not is_valid_subdomain('foo_bar')  # invalid char
    assert not is_valid_subdomain('-foo')  # starts with hyphen
    assert not is_valid_subdomain('foo-')  # ends with hyphen
    assert not is_valid_subdomain('www')  # reserved
    assert not is_valid_subdomain('')
