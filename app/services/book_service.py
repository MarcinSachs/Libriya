"""
Book search service orchestrator.

Searches books with tiered priority:
1. Premium Biblioteka Narodowa (Polish National Library) - if enabled
2. Open Library (fallback if BN has no data)
3. Premium covers (Bookcover API) - if enabled
4. Open Library covers (fallback)

Usage:
    book = BookSearchService.search_by_isbn("9788375799538")
    results = BookSearchService.search_by_title("The Hobbit")
"""

from typing import List, Dict, Optional
from app.services.openlibrary_service import OpenLibraryClient
from app.services.cover_service import CoverService
from app.services.isbn_validator import ISBNValidator
from app.services.premium.manager import PremiumManager
import logging

logger = logging.getLogger(__name__)


class BookSearchService:
    """Main service for searching books with premium source support."""

    @staticmethod
    def search_by_isbn(isbn: str) -> Optional[Dict]:
        """
        Search for book by ISBN with tiered source priority.

        Priority:
        1. Biblioteka Narodowa (Premium) - if enabled
        2. Open Library (fallback if BN has no data or not enabled)
        3. Premium covers - if enabled
        4. Open Library covers (fallback)

        Args:
            isbn: ISBN number (10 or 13)

        Returns:
            Unified book data dict with cover info, or None if not found
        """
        if not isbn:
            return None

        # Validate ISBN
        if not ISBNValidator.is_valid(isbn):
            logger.warning(f"BookSearchService: Invalid ISBN: {isbn}")
            return None

        normalized_isbn = ISBNValidator.normalize(isbn)
        logger.info(f"BookSearchService: Searching ISBN: {normalized_isbn}")

        book_data = None

        # 1. Try Biblioteka Narodowa FIRST (if enabled)
        if PremiumManager.is_enabled('metadata'):
            logger.debug(f"BookSearchService: Trying Biblioteka Narodowa for ISBN {normalized_isbn}")
            book_data = PremiumManager.call(
                'metadata',
                'BibliotekaNarodowaService',
                'search_by_isbn',
                isbn=normalized_isbn
            )
            if book_data:
                logger.info(f"BookSearchService: Found in BN: {book_data.get('title')}")
                # Enhance with cover (OL or premium)
                BookSearchService._enhance_with_cover(book_data, normalized_isbn)
                return book_data
            else:
                logger.info("BookSearchService: Not found in BN, falling back to Open Library")

        # 2. Try Open Library (fallback)
        logger.debug(f"BookSearchService: Searching Open Library for ISBN {normalized_isbn}")
        book_data = OpenLibraryClient.search_by_isbn(normalized_isbn)

        if book_data:
            logger.info(f"BookSearchService: Found in OL: {book_data.get('title')}")
            # Enhance with cover
            BookSearchService._enhance_with_cover(book_data, normalized_isbn)
            return book_data

        # If Open Library has no data, try premium sources for cover only
        logger.info("BookSearchService: Book not found in any source")
        logger.debug(f"BookSearchService: Trying premium cover sources for ISBN {normalized_isbn}")
        cover_url = CoverService._get_cover_from_premium_sources(isbn=normalized_isbn)

        if cover_url:
            logger.info(f"BookSearchService: Found cover in premium sources for ISBN {normalized_isbn}")
            # Return minimal book data with cover from premium
            return {
                "isbn": normalized_isbn,
                "title": None,  # No metadata available
                "authors": [],
                "year": None,
                "publisher": None,
                "source": "premium_cover_only",
                "cover": {
                    "url": cover_url,
                    "source": "premium_bookcover"
                }
            }

        logger.info(f"BookSearchService: No data found for ISBN {normalized_isbn}")
        return None

    @staticmethod
    def search_by_title(
        title: str,
        author: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Search for books by title in Open Library.

        Note: Biblioteka Narodowa doesn't have a good title search API,
        so we only use Open Library for title searches.

        Args:
            title: Book title (min 3 characters)
            author: Author name (optional, not used in OL search)
            limit: Max results to return

        Returns:
            List of unified book data dicts
        """
        if not title or len(title.strip()) < 3:
            logger.warning(f"BookSearchService: Invalid title query: {title}")
            return []

        logger.info(f"BookSearchService: Searching by title in Open Library: '{title}'")

        # Search in Open Library
        ol_results = OpenLibraryClient.search_by_title(title, limit)

        # Enhance each result with cover info
        for result in ol_results:
            BookSearchService._enhance_with_cover(result)

        logger.info(f"BookSearchService: Found {len(ol_results)} results")
        return ol_results

    @staticmethod
    def _enhance_with_cover(
        book_data: Dict,
        isbn: Optional[str] = None
    ) -> None:
        """
        Enhance book data with cover information.

        Uses CoverService which handles the tiered cover priority:
        1. Premium bookcover (if enabled and licensed)
        2. Cover from metadata (OL)
        3. Open Library ISBN lookup
        4. Local default

        Modifies book_data in place to add/update cover info.

        Args:
            book_data: Book data dict (from BN or OL)
            isbn: ISBN if not in book_data
        """
        try:
            isbn = isbn or book_data.get("isbn")
            title = book_data.get("title")
            authors = book_data.get("authors", [])
            author = authors[0] if authors else None

            # Get cover from existing source or find new one
            existing_cover = book_data.get("cover")

            cover_url, cover_source = CoverService.get_cover_url(
                isbn=isbn,
                title=title,
                author=author,
                cover_from_source=existing_cover
            )

            # Update or create cover info
            if not book_data.get("cover"):
                book_data["cover"] = {}

            if isinstance(book_data["cover"], str):
                book_data["cover"] = {"url": book_data["cover"], "source": "open_library"}

            if isinstance(book_data["cover"], dict):
                book_data["cover"]["url"] = cover_url
                book_data["cover"]["source"] = cover_source
            else:
                book_data["cover"] = {
                    "url": cover_url,
                    "source": cover_source
                }

            logger.debug(f"BookSearchService: Enhanced cover for '{title}': {cover_source}")

        except Exception as e:
            logger.error(f"BookSearchService: Error enhancing cover: {e}")
            # Don't fail entire search if cover fails
            book_data["cover"] = {"url": None, "source": "local_default"}
