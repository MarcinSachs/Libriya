"""
Book cover service.

Manages downloading and storing book covers from multiple sources:
1. Open Library (if data source is OL)
2. Bookcover API (Goodreads via bookcover.longitood.com)
3. Local default fallback image
"""

import requests
import os
import secrets
from typing import Optional, Tuple
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class CoverService:
    """Service for managing book covers from multiple sources."""

    # URLs
    BOOKCOVER_API_URL = "https://bookcover.longitood.com/bookcover"
    DEFAULT_COVER_FILENAME = "default-book-cover.png"

    # Limits
    MAX_COVER_SIZE = 5 * 1024 * 1024  # 5MB
    ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif']
    TIMEOUT = 5

    @staticmethod
    def get_cover_url(
        isbn: Optional[str] = None,
        title: Optional[str] = None,
        author: Optional[str] = None,
        cover_from_source: Optional[str] = None,
        source_cover_data: Optional[str] = None
    ) -> Tuple[Optional[str], str]:
        """
        Get cover URL based on priority: OL (source) → OL (ISBN) → Bookcover API → Default.

        Args:
            isbn: ISBN number
            title: Book title
            author: Book author
            cover_from_source: Cover URL from data source (e.g., Open Library)
            source_cover_data: Additional cover data (e.g., cover_id from OL)

        Returns:
            Tuple of (cover_url, source) where source is one of:
            'open_library', 'bookcover_api', 'local_default', None
        """
        logger.info(f"CoverService: Getting cover for: {title or isbn}")

        # 1. Try Open Library cover (if data is from OL)
        if cover_from_source:
            logger.info(f"CoverService: Using cover from source: {cover_from_source[:50]}...")
            return cover_from_source, "open_library"

        # 2. Try Open Library by ISBN (when source has no cover but ISBN is available)
        if isbn:
            cover_url = CoverService._get_cover_from_openlibrary_by_isbn(isbn)
            if cover_url:
                logger.info(f"CoverService: Got cover from Open Library (ISBN lookup)")
                return cover_url, "open_library"

        # 3. Try Bookcover API (searches Goodreads)
        if isbn or (title and author):
            cover_url = CoverService._get_cover_from_bookcover_api(isbn, title, author)
            if cover_url:
                logger.info(f"CoverService: Got cover from Bookcover API")
                return cover_url, "bookcover_api"

        # 4. Fallback to local default image
        logger.info(f"CoverService: Using local default cover")
        return None, "local_default"

    @staticmethod
    def _get_cover_from_bookcover_api(
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
                url = CoverService._try_bookcover_isbn(isbn)
                if url:
                    return url

            # Try by title and author
            if title and author:
                url = CoverService._try_bookcover_title_author(title, author)
                if url:
                    return url

            return None

        except Exception as e:
            logger.warning(f"CoverService: Bookcover API error: {e}")
            return None

    @staticmethod
    def _try_bookcover_isbn(isbn: str) -> Optional[str]:
        """Try to get cover by ISBN from Bookcover API."""
        try:
            response = requests.get(
                f"{CoverService.BOOKCOVER_API_URL}/{isbn}",
                timeout=CoverService.TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                url = data.get("url")
                if url:
                    logger.info(f"CoverService: Found cover for ISBN {isbn}")
                    return url
        except Exception as e:
            logger.debug(f"CoverService: Bookcover ISBN lookup failed: {e}")

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
                CoverService.BOOKCOVER_API_URL,
                params=params,
                timeout=CoverService.TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                url = data.get("url")
                if url:
                    logger.info(f"CoverService: Found cover for '{title}' by {author}")
                    return url
        except Exception as e:
            logger.debug(f"CoverService: Bookcover title/author lookup failed: {e}")

        return None

    @staticmethod
    def _get_cover_from_openlibrary_by_isbn(isbn: str) -> Optional[str]:
        """
        Get cover from Open Library by ISBN lookup.

        Queries Open Library API for book data and extracts thumbnail URL.

        Args:
            isbn: ISBN number

        Returns:
            Cover URL (thumbnail_url) or None if not found
        """
        try:
            params = {
                "bibkeys": f"ISBN:{isbn}",
                "jscmd": "data",
                "format": "json"
            }

            response = requests.get(
                "https://openlibrary.org/api/books",
                params=params,
                timeout=CoverService.TIMEOUT
            )
            response.raise_for_status()

            data = response.json()
            book_data = data.get(f"ISBN:{isbn}")

            if not book_data:
                logger.debug(f"CoverService: Open Library has no data for ISBN {isbn}")
                return None

            # Try to get thumbnail URL
            covers = book_data.get("cover", {})
            if isinstance(covers, dict):
                thumbnail_url = covers.get("large") or covers.get("medium") or covers.get("small")
                if thumbnail_url:
                    logger.info(f"CoverService: Found Open Library thumbnail for ISBN {isbn}")
                    return thumbnail_url

            logger.debug(f"CoverService: Open Library has no cover for ISBN {isbn}")
            return None

        except requests.exceptions.Timeout:
            logger.debug(f"CoverService: Open Library timeout for ISBN {isbn}")
            return None
        except requests.exceptions.RequestException as e:
            logger.debug(f"CoverService: Open Library API error for ISBN {isbn}: {e}")
            return None
        except Exception as e:
            logger.debug(f"CoverService: Error getting OL cover for ISBN {isbn}: {e}")
            return None

    @staticmethod
    def download_and_save_cover(
        cover_url: str,
        upload_folder: str
    ) -> Optional[str]:
        """
        Download cover image from URL and save locally.

        Args:
            cover_url: URL to download from
            upload_folder: Local folder to save to

        Returns:
            Filename if successful, None otherwise
        """
        try:
            logger.info(f"CoverService: Downloading cover from {cover_url[:50]}...")

            # Validate URL
            if not CoverService._validate_url(cover_url):
                logger.warning(f"CoverService: Invalid URL: {cover_url}")
                return None

            # Download with security checks
            response = requests.get(cover_url, stream=True, timeout=CoverService.TIMEOUT)
            response.raise_for_status()

            if response.status_code != 200:
                logger.warning(f"CoverService: Bad status code {response.status_code}")
                return None

            # Check content-length
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > CoverService.MAX_COVER_SIZE:
                logger.warning(f"CoverService: File too large: {content_length} bytes")
                return None

            # Download with size limit
            content = b''
            for chunk in response.iter_content(chunk_size=1024):
                content += chunk
                if len(content) > CoverService.MAX_COVER_SIZE:
                    logger.warning(f"CoverService: Downloaded content exceeds limit")
                    return None

            # Determine file extension
            _, f_ext = os.path.splitext(urlparse(cover_url).path)
            if not f_ext or f_ext.lower() not in CoverService.ALLOWED_EXTENSIONS:
                f_ext = '.jpg'

            # Save file
            random_hex = secrets.token_hex(8)
            filename = random_hex + f_ext
            filepath = os.path.join(upload_folder, filename)

            with open(filepath, 'wb') as f:
                f.write(content)

            logger.info(f"CoverService: Saved cover as {filename}")
            return filename

        except requests.exceptions.Timeout:
            logger.warning(f"CoverService: Download timeout for {cover_url[:50]}...")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"CoverService: Download error: {e}")
            return None
        except Exception as e:
            logger.error(f"CoverService: Save error: {e}")
            return None

    @staticmethod
    def _validate_url(url: str) -> bool:
        """
        Validate URL for security (prevent SSRF).

        Args:
            url: URL to validate

        Returns:
            True if URL is safe, False otherwise
        """
        try:
            parsed_url = urlparse(url)

            # Check protocol
            if parsed_url.scheme not in ['http', 'https']:
                return False

            # Block localhost and private IPs
            blocked_hosts = ['localhost', '127.0.0.1', '0.0.0.0', 'l.longitood.com']
            if parsed_url.netloc in blocked_hosts:
                return False

            # Check for private IP ranges
            import ipaddress
            try:
                ip = ipaddress.ip_address(parsed_url.hostname)
                if ip.is_private or ip.is_loopback:
                    return False
            except (ValueError, TypeError):
                # If hostname is not an IP, it's likely a domain name (OK)
                pass

            return True

        except Exception:
            return False
