"""
Bookcover API service (Goodreads covers via bookcover.longitood.com).

Premium feature - requires license/subscription.
See: https://bookcover.longitood.com/
"""

import requests
from typing import Optional
import logging
from app.services.isbn_validator import ISBNValidator

logger = logging.getLogger(__name__)


class BookcoverService:
    """Service for Bookcover API (Goodreads covers)."""

    # API endpoint
    API_URL = "https://bookcover.longitood.com/bookcover"

    # Timeout
    TIMEOUT = 5

    @staticmethod
    def get_cover_from_bookcover_api(
        isbn: Optional[str] = None,
        title: Optional[str] = None,
        author: Optional[str] = None
    ) -> Optional[str]:
        """
        Get cover from Bookcover API (Goodreads).

        Tries ISBN first, then title+author.

        Args:
            isbn: ISBN number
            title: Book title
            author: Book author

        Returns:
            Cover URL or None if not found
        """
        try:
            # Try by ISBN first
            if isbn:
                url = BookcoverService._try_bookcover_isbn(isbn)
                if url:
                    return url

            # Try by title and author
            if title and author:
                url = BookcoverService._try_bookcover_title_author(title, author)
                if url:
                    return url

            return None

        except Exception as e:
            logger.warning(f"BookcoverService: API error: {e}")
            return None

    @staticmethod
    def _try_bookcover_isbn(isbn: str) -> Optional[str]:
        """Try to get cover by ISBN from Bookcover API."""
        try:
            # Convert ISBN-10 to ISBN-13 if needed
            isbn_13 = ISBNValidator.to_isbn_13(isbn)

            response = requests.get(
                f"{BookcoverService.API_URL}/{isbn_13}",
                timeout=BookcoverService.TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                url = data.get("url")
                if url:
                    logger.info(f"BookcoverService: Found cover for ISBN {isbn} (converted to {isbn_13})")
                    return url
        except Exception as e:
            logger.debug(f"BookcoverService: ISBN lookup failed: {e}")

        return None

    @staticmethod
    def _try_bookcover_title_author(title: str, author: str) -> Optional[str]:
        """Try to get cover by title and author from Bookcover API."""
        try:
            params = {
                "book_title": title,
                "author_name": author
            }

            response = requests.get(
                BookcoverService.API_URL,
                params=params,
                timeout=BookcoverService.TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                url = data.get("url")
                if url:
                    logger.info(f"BookcoverService: Found cover for '{title}' by {author}")
                    return url
        except Exception as e:
            logger.debug(f"BookcoverService: Title/author lookup failed: {e}")

        return None
