import pytest
from app.services.isbn_validator import ISBNValidator

def test_isbn_normalize():
    assert ISBNValidator.normalize('978-0-545-00395-7') == '9780545003957'
    assert ISBNValidator.normalize(' 978 0 545 00395 7 ') == '9780545003957'

def test_isbn10_valid():
    assert ISBNValidator.is_valid('048665088X')
    assert not ISBNValidator.is_valid('0486650880')

def test_isbn13_valid():
    assert ISBNValidator.is_valid('9780545003957')
    assert not ISBNValidator.is_valid('9780545003958')

def test_isbn_format_isbn_13():
    assert ISBNValidator.format_isbn_13('9780545003957') == '978-0-545-00395-7'
    assert ISBNValidator.format_isbn_13('048665088X').startswith('978-0-486-65088')
