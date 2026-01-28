"""
Main book search service orchestrator.

Coordinates searching across multiple databases and cover sources with proper
fallback logic and unified response format.
"""

from typing import List, Dict, Optional, Tuple
from app.services.bn_api import BNAPIClient
from app.services.openlibrary_service import OpenLibraryClient
from app.services.cover_service import CoverService
from app.services.isbn_validator import ISBNValidator
import logging

logger = logging.getLogger(__name__)


class BookSearchService:
    """Main service for searching books across multiple sources."""

    @staticmethod
    def search_by_isbn(
        isbn: str,
        use_bn: bool = True,
        use_openlibrary: bool = True
    ) -> Optional[Dict]:
        """
        Search for book by ISBN with fallback logic.

        Priority:
        1. Biblioteka Narodowa (combined catalogs)
        2. Open Library API
        3. None if not found anywhere

        Args:
            isbn: ISBN number (10 or 13)
            use_bn: Try BN first if True
            use_openlibrary: Fallback to Open Library if True

        Returns:
            Unified book data dict with cover info, or None if not found
        """
        if not isbn:
            return None

        # Validate ISBN
        is_valid, formatted_isbn = ISBNValidator.normalize(isbn), isbn
        if not ISBNValidator.is_valid(isbn):
            logger.warning(f"BookSearchService: Invalid ISBN: {isbn}")
            return None

        normalized_isbn = ISBNValidator.normalize(isbn)
        logger.info(f"BookSearchService: Search by ISBN: {normalized_isbn}")

        book_data = None
        source_used = None

        # 1. Try BN first
        if use_bn:
            book_data = BNAPIClient.search_by_isbn(normalized_isbn)
            if book_data:
                source_used = "bn"
                logger.info(f"BookSearchService: Found in BN: {book_data.get('title')}")

        # 2. Fallback to Open Library
        if not book_data and use_openlibrary:
            book_data = OpenLibraryClient.search_by_isbn(normalized_isbn)
            if book_data:
                source_used = "open_library"
                logger.info(f"BookSearchService: Found in Open Library: {book_data.get('title')}")

        if not book_data:
            logger.info(f"BookSearchService: Not found in any source")
            return None

        # Enhance with cover
        BookSearchService._enhance_with_cover(book_data, normalized_isbn)

        return book_data

    @staticmethod
    def search_by_title(
        title: str,
        author: Optional[str] = None,
        limit: int = 10,
        use_bn: bool = True,
        use_openlibrary: bool = True
    ) -> List[Dict]:
        """
        Search for books by title with fallback logic.

        Priority:
        1. Biblioteka Narodowa (combined catalogs)
        2. Open Library API
        3. Merge and deduplicate results

        Args:
            title: Book title (min 3 characters)
            author: Author name (optional)
            limit: Max results to return
            use_bn: Try BN first if True
            use_openlibrary: Try Open Library if True

        Returns:
            List of unified book data dicts
        """
        if not title or len(title.strip()) < 3:
            logger.warning(f"BookSearchService: Invalid title query: {title}")
            return []

        logger.info(f"BookSearchService: Search by title: '{title}', author: '{author}'")

        results = []
        seen_isbns = set()

        # 1. Try BN first
        if use_bn:
            bn_results = BNAPIClient.search_by_title(title, author, limit)
            for result in bn_results:
                isbn = result.get("isbn")
                if isbn and isbn not in seen_isbns:
                    BookSearchService._enhance_with_cover(result)
                    results.append(result)
                    seen_isbns.add(isbn)
            logger.info(f"BookSearchService: BN returned {len(bn_results)} results")

        # 2. Try Open Library (to fill gaps)
        if len(results) < limit and use_openlibrary:
            ol_results = OpenLibraryClient.search_by_title(title, limit - len(results))
            for result in ol_results:
                isbn = result.get("isbn")
                if isbn and isbn not in seen_isbns:
                    BookSearchService._enhance_with_cover(result)
                    results.append(result)
                    seen_isbns.add(isbn)
            logger.info(f"BookSearchService: Open Library returned {len(ol_results)} results")

        logger.info(f"BookSearchService: Total results: {len(results)}")
        return results[:limit]

    @staticmethod
    def _enhance_with_cover(
        book_data: Dict,
        isbn: Optional[str] = None
    ) -> None:
        """
        Enhance book data with cover information.

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
