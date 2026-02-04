"""
Biblioteka Narodowa Integration - Usage Examples

Examples and test cases for the BN premium module.
"""

# ============================================================================
# EXAMPLE 1: Enable the Module
# ============================================================================

# .env file:
"""
PREMIUM_BIBLIOTEKA_NARODOWA_ENABLED=true
PREMIUM_BOOKCOVER_ENABLED=true
"""

# ============================================================================
# EXAMPLE 2: Automatic Integration with BookSearchService
# ============================================================================


# Search for a Polish book
# This automatically tries BN first, then Open Library
from app.services.book_service import BookSearchService
from app.services.premium.manager import PremiumManager
import logging
from app.models import Book
book = BookSearchService.search_by_isbn("9788375799538")

if book:
    print(f"Title: {book['title']}")
    print(f"Authors: {book['authors']}")
    print(f"Year: {book['year']}")
    print(f"Publisher: {book['publisher']}")
    print(f"Genres: {book.get('genres', [])}")
    print(f"Source: {book['source']}")  # 'biblioteka_narodowa' or 'open_library'
    print(f"Cover: {book['cover']['source']}")  # 'premium_bookcover' or 'open_library'


# ============================================================================
# EXAMPLE 3: Direct Service Access
# ============================================================================


# Check if BN is enabled
if PremiumManager.is_enabled('biblioteka_narodowa'):
    # Call the service directly
    result = PremiumManager.call(
        'biblioteka_narodowa',
        'search_by_isbn',
        isbn='9788375799538'
    )

    if result:
        print(f"✓ Found in BN: {result['title']}")
        print(f"  BN ID: {result['bn_id']}")
        print(f"  Genres: {result['genres']}")
    else:
        print("✗ Not found in BN - should try Open Library")
else:
    print("BN module is disabled")


# ============================================================================
# EXAMPLE 4: Testing with Various Polish Books
# ============================================================================

TEST_BOOKS = [
    {
        "isbn": "9788375799538",
        "title": "Wiedzmin: Ostatnie zyczenie",
        "expected_genre": "Fantasy"
    },
    {
        "isbn": "9788301058715",
        "title": "Zbrodnia i kara",
        "expected_genre": "Crime / Thriller"
    },
    {
        "isbn": "9788310134884",
        "title": "Pani Bovary",
        "expected_genre": "Fiction"
    },
]

for book_info in TEST_BOOKS:
    book = BookSearchService.search_by_isbn(book_info["isbn"])

    if book:
        print(f"\n✓ {book_info['title']}")
        print(f"  ISBN: {book['isbn']}")
        print(f"  Source: {book['source']}")
        print(f"  Authors: {', '.join(book['authors'])}")
        print(f"  Year: {book['year']}")
        print(f"  Genres: {', '.join(book.get('genres', []))}")
    else:
        print(f"\n✗ Not found: {book_info['title']}")


# ============================================================================
# EXAMPLE 5: Error Handling
# ============================================================================

def search_with_fallback(isbn):
    """Search for book, handle all error cases."""

    if not isbn:
        print("Error: ISBN is required")
        return None

    try:
        book = BookSearchService.search_by_isbn(isbn)

        if not book:
            print(f"Book not found for ISBN: {isbn}")
            return None

        # Check source
        if book['source'] == 'biblioteka_narodowa':
            print(f"✓ Using enriched BN data for {book['title']}")
        elif book['source'] == 'open_library':
            print(f"℮ Using Open Library data for {book['title']}")
        elif book['source'] == 'premium_cover_only':
            print(f"⚠ Only cover available from premium sources")

        # Check cover
        if book['cover']['source'] == 'premium_bookcover':
            print(f"  Cover: Premium (Goodreads)")
        elif book['cover']['source'] == 'open_library':
            print(f"  Cover: Open Library")
        else:
            print(f"  Cover: Default/Local")

        return book

    except Exception as e:
        print(f"Error searching for ISBN {isbn}: {e}")
        return None


# Usage
search_with_fallback("9788375799538")


# ============================================================================
# EXAMPLE 6: Integration with Book Model
# ============================================================================


def create_book_from_search(isbn):
    """Create a book record using search results."""

    book_data = BookSearchService.search_by_isbn(isbn)

    if not book_data:
        return None

    # Create new book with enriched data
    book = Book(
        isbn=book_data['isbn'],
        title=book_data['title'],
        authors_str='; '.join(book_data['authors']),
        year=book_data['year'],
        publisher=book_data['publisher'],
        cover_url=book_data['cover']['url'],
        cover_source=book_data['cover']['source'],
        # Add source as custom field if your model supports it
        metadata_source=book_data['source']
    )

    return book


# ============================================================================
# EXAMPLE 7: Monitoring and Logging
# ============================================================================


logger = logging.getLogger(__name__)


def search_with_monitoring(isbn):
    """Search with detailed logging for monitoring."""

    logger.info(f"Searching for ISBN: {isbn}")

    # Check if BN is enabled
    if PremiumManager.is_enabled('biblioteka_narodowa'):
        logger.info("BN module is ENABLED")
    else:
        logger.warning("BN module is DISABLED")

    book = BookSearchService.search_by_isbn(isbn)

    if book:
        logger.info(
            f"Book found",
            extra={
                'isbn': isbn,
                'title': book['title'],
                'source': book['source'],
                'cover_source': book['cover']['source'],
                'authors': len(book['authors']),
                'genres': len(book.get('genres', [])),
            }
        )
    else:
        logger.warning(f"Book not found for ISBN: {isbn}")

    return book


# ============================================================================
# EXAMPLE 8: Checking Module Status
# ============================================================================

def check_premium_modules():
    """Check status of all premium modules."""

    features = PremiumManager.list_features()
    enabled = PremiumManager.get_enabled_features()

    print("Available Premium Features:")
    for feature_id, info in features.items():
        status = "✓ ENABLED" if feature_id in enabled else "✗ DISABLED"
        print(f"  {status}: {info['name']}")

    # Detailed info about BN
    bn_info = PremiumManager.feature_info('biblioteka_narodowa')
    if bn_info:
        print(f"\nBiblioteka Narodowa Details:")
        print(f"  Name: {bn_info['name']}")
        print(f"  Description: {bn_info['description']}")
        print(f"  Enabled: {bn_info['enabled']}")
        print(f"  Env Var: {bn_info['enabled_env_var']}")


# ============================================================================
# EXAMPLE 9: Bulk Search
# ============================================================================

def bulk_search(isbn_list):
    """Search multiple books and report results."""

    results = {
        'found_bn': [],
        'found_ol': [],
        'not_found': [],
        'errors': []
    }

    for isbn in isbn_list:
        try:
            book = BookSearchService.search_by_isbn(isbn)

            if not book:
                results['not_found'].append(isbn)
            elif book['source'] == 'biblioteka_narodowa':
                results['found_bn'].append({
                    'isbn': isbn,
                    'title': book['title'],
                    'bn_id': book.get('bn_id')
                })
            else:
                results['found_ol'].append({
                    'isbn': isbn,
                    'title': book['title']
                })

        except Exception as e:
            results['errors'].append({'isbn': isbn, 'error': str(e)})

    return results


# Usage
results = bulk_search([
    "9788375799538",
    "9788301058715",
    "0000000000",  # Invalid
])

print(f"Found in BN: {len(results['found_bn'])}")
print(f"Found in OL: {len(results['found_ol'])}")
print(f"Not found: {len(results['not_found'])}")
print(f"Errors: {len(results['errors'])}")


# ============================================================================
# EXAMPLE 10: Fallback Behavior
# ============================================================================

def test_fallback_behavior():
    """Test how fallback works when BN doesn't have the book."""

    # This book might not be in Polish National Library
    # but should be found in Open Library
    english_book_isbn = "9780545003957"  # The Hobbit

    book = BookSearchService.search_by_isbn(english_book_isbn)

    if book:
        print(f"Book: {book['title']}")
        print(f"Source: {book['source']}")

        if book['source'] == 'open_library':
            print("✓ Fallback worked: Book found in Open Library")
        else:
            print("✓ Book found in BN (unlikely for English books)")
    else:
        print("✗ Book not found in any source")


# ============================================================================
# TEST CASES
# ============================================================================

if __name__ == "__main__":
    print("Running BN Integration Examples...\n")

    print("=" * 60)
    print("TEST 1: Check Module Status")
    print("=" * 60)
    check_premium_modules()

    print("\n" + "=" * 60)
    print("TEST 2: Search Polish Book")
    print("=" * 60)
    search_with_monitoring("9788375799538")

    print("\n" + "=" * 60)
    print("TEST 3: Fallback Behavior")
    print("=" * 60)
    test_fallback_behavior()

    print("\n" + "=" * 60)
    print("TEST 4: Bulk Search Results")
    print("=" * 60)
    results = bulk_search([
        "9788375799538",
        "9788301058715",
        "9780545003957",
    ])
    print(f"\nResults:")
    print(f"  From BN: {len(results['found_bn'])}")
    print(f"  From OL: {len(results['found_ol'])}")
    print(f"  Not found: {len(results['not_found'])}")
