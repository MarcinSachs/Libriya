"""
Book cover service.

Manages downloading and storing book covers with tiered fallback:
1. Open Library (always available)
2. Premium sources (if enabled and licensed, e.g., bookcover.longitood.com)
3. Local default image

Premium covers transparently extend base functionality without code changes.
"""

import requests
import os
import secrets
from typing import Optional, Tuple
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class CoverService:
    """Service for managing book covers from Open Library."""

    # URLs
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
        Get cover URL with tiered fallback strategy.

        Priority:
        1. Premium sources (if enabled and licensed):
           - bookcover.longitood.com (Goodreads)
        2. Cover from Open Library metadata (cover_from_source)
        3. Cover from Open Library by ISBN lookup
        4. Local default image

        Args:
            isbn: ISBN number
            title: Book title
            author: Book author
            cover_from_source: Cover URL from Open Library metadata
            source_cover_data: Cover ID from Open Library (not used)

        Returns:
            Tuple of (cover_url, source) where source is:
            'open_library', 'premium_bookcover', 'local_default', or None
        """
        logger.info(f"CoverService: Getting cover for: {title or isbn}")

        # 1. Try premium sources FIRST (if enabled and licensed)
        cover_url = CoverService._get_cover_from_premium_sources(isbn, title, author)
        if cover_url:
            logger.info(f"CoverService: Got premium cover from premium sources")
            return cover_url, "premium_bookcover"

        # 2. Try cover from source (Open Library metadata)
        if cover_from_source:
            logger.info(f"CoverService: Using OL cover from metadata")
            return cover_from_source, "open_library"

        # 3. Try Open Library by ISBN lookup
        if isbn:
            cover_url = CoverService._get_cover_from_openlibrary_by_isbn(isbn)
            if cover_url:
                logger.info(f"CoverService: Got cover from Open Library (ISBN lookup)")
                return cover_url, "open_library"

        # 4. Fallback to local default image
        logger.info(f"CoverService: Using local default cover")
        return None, "local_default"

    @staticmethod
    def _get_cover_from_premium_sources(
        isbn: Optional[str] = None,
        title: Optional[str] = None,
        author: Optional[str] = None
    ) -> Optional[str]:
        """
        Try to get cover from premium sources.

        This method transparently uses premium features if they're enabled and licensed.
        No code changes needed when adding new premium cover sources!

        Args:
            isbn: ISBN number
            title: Book title
            author: Book author

        Returns:
            Cover URL or None if not found or premium not available
        """
        # Import here to avoid circular imports
        from app.services.premium.manager import PremiumManager

        # Try bookcover API (Goodreads) - premium source
        if PremiumManager.is_enabled('bookcover_api'):
            logger.info("CoverService: Trying premium bookcover API")
            cover_url = PremiumManager.call(
                'bookcover_api',
                'get_cover_from_bookcover_api',
                isbn=isbn,
                title=title,
                author=author
            )
            if cover_url:
                logger.info("CoverService: Got premium cover from bookcover API")
                return cover_url
        else:
            logger.info("CoverService: bookcover_api premium feature is not enabled")

        # Future: Add more premium sources here
        # if PremiumManager.is_enabled('another_premium_source'):
        #     cover_url = PremiumManager.call(...)
        #     if cover_url:
        #         return cover_url

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
                    logger.warning("CoverService: Downloaded content exceeds limit")
                    return None

            # Determine file extension
            _, f_ext = os.path.splitext(urlparse(cover_url).path)
            if not f_ext or f_ext.lower() not in CoverService.ALLOWED_EXTENSIONS:
                f_ext = '.jpg'

            # Random filename
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
