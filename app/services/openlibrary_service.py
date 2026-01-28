"""
Open Library API client.

Integration with Open Library API for searching books and covers.
Documentation: https://openlibrary.org/dev/docs/api/books
"""

import requests
from typing import List, Dict, Optional
import logging
import re

logger = logging.getLogger(__name__)


class OpenLibraryClient:
    """Client for Open Library API."""

    # API endpoints
    ISBN_API_URL = "https://openlibrary.org/api/books"
    SEARCH_API_URL = "https://openlibrary.org/search.json"
    COVERS_URL = "https://covers.openlibrary.org/b"

    # Timeouts
    TIMEOUT = 10

    @staticmethod
    def search_by_isbn(isbn: str) -> Optional[Dict]:
        """
        Search for book by ISBN in Open Library.

        Args:
            isbn: ISBN number (10 or 13 digits)

        Returns:
            Book data dict or None if not found
        """
        logger.info(f"Open Library: Searching by ISBN: {isbn}")

        try:
            params = {
                "bibkeys": f"ISBN:{isbn}",
                "jscmd": "data",
                "format": "json"
            }

            response = requests.get(
                OpenLibraryClient.ISBN_API_URL,
                params=params,
                timeout=OpenLibraryClient.TIMEOUT
            )
            response.raise_for_status()

            data = response.json()
            book_data = data.get(f"ISBN:{isbn}")

            if not book_data:
                logger.info(f"Open Library: No data for ISBN {isbn}")
                return None

            parsed = OpenLibraryClient._parse_book_data(book_data, isbn)
            logger.info(f"Open Library: Found book: {parsed['title']}")
            return parsed

        except requests.exceptions.Timeout:
            logger.warning(f"Open Library timeout for ISBN: {isbn}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Open Library API error for ISBN {isbn}: {e}")
            return None
        except Exception as e:
            logger.error(f"Open Library parsing error: {e}")
            return None

    @staticmethod
    def search_by_title(
        query: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Search for books by title in Open Library.

        Args:
            query: Search query (min 3 characters)
            limit: Max results (capped at 20)

        Returns:
            List of book data dicts
        """
        if not query or len(query.strip()) < 3:
            return []

        logger.info(f"Open Library: Searching by title: '{query}'")

        try:
            params = {
                "title": query,
                "limit": min(limit, 20),
                "fields": "title,author_name,first_publish_year,isbn,cover_i"
            }

            response = requests.get(
                OpenLibraryClient.SEARCH_API_URL,
                params=params,
                timeout=OpenLibraryClient.TIMEOUT
            )
            response.raise_for_status()

            data = response.json()
            docs = data.get("docs", [])

            results = []
            for doc in docs[:limit]:
                isbn_list = doc.get("isbn", [])
                if isbn_list:  # Only return books with ISBN
                    parsed = {
                        "source": "open_library",
                        "title": doc.get("title"),
                        "authors": doc.get("author_name", []),
                        "isbn": isbn_list[0],
                        "year": doc.get("first_publish_year"),
                        "cover_id": doc.get("cover_i"),
                    }
                    results.append(parsed)

            logger.info(f"Open Library: Found {len(results)} results")
            return results

        except requests.exceptions.Timeout:
            logger.warning(f"Open Library timeout for query: {query}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Open Library API error for query '{query}': {e}")
            return []
        except Exception as e:
            logger.error(f"Open Library parsing error: {e}")
            return []

    @staticmethod
    def _parse_book_data(book_data: Dict, isbn: str) -> Optional[Dict]:
        """
        Parse Open Library book data into standardized format.

        Args:
            book_data: Raw Open Library data
            isbn: ISBN used for lookup

        Returns:
            Standardized book data dict
        """
        try:
            title = book_data.get("title", "").strip()
            authors = []
            for author in book_data.get("authors", []):
                author_name = author.get("name", "").strip()
                if author_name:
                    authors.append(author_name)

            # Extract year from publish_date
            year = None
            publish_date = book_data.get("publish_date", "")
            if publish_date:
                match = re.search(r'\d{4}', publish_date)
                if match:
                    year = int(match.group(0))

            # Get cover URL
            cover_url = None
            covers = book_data.get("cover", {})
            if isinstance(covers, dict):
                cover_url = covers.get("large") or covers.get("medium")

            publisher = ""
            publishers = book_data.get("publishers", [])
            if publishers:
                publisher = publishers[0].get("name", "") if isinstance(publishers[0], dict) else publishers[0]

            return {
                "source": "open_library",
                "source_id": book_data.get("key"),
                "title": title,
                "authors": authors,
                "isbn": isbn,
                "publisher": publisher,
                "year": year,
                "language": book_data.get("languages", [{}])[0].get("key", "").replace("/languages/", "") if book_data.get("languages") else None,
                "cover": cover_url,
                "number_of_pages": book_data.get("number_of_pages"),
            }

        except Exception as e:
            logger.error(f"Error parsing Open Library data: {e}")
            return None

    @staticmethod
    def get_cover_url(cover_id: int, size: str = "M") -> str:
        """
        Get Open Library cover URL.

        Args:
            cover_id: Cover ID from Open Library
            size: Size: S (small), M (medium), L (large)

        Returns:
            Cover image URL
        """
        return f"{OpenLibraryClient.COVERS_URL}/id/{cover_id}-{size}.jpg"
