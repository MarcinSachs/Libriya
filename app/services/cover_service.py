"""
Book cover service.

Manages downloading and storing book covers with tiered fallback strategy:

Priority:
1. Premium Bookcover API (if enabled and licensed) - bookcover.longitood.com
2. Cover from source metadata (e.g., Open Library)
3. Cover from Open Library by ISBN lookup
4. Local default image

Notes:
- Biblioteka Narodowa doesn't provide covers, so covers always come from OL/premium
- Premium bookcover service has HIGHEST priority when enabled and licensed
- If no premium cover found, falls back to Open Library
- If Open Library has no data, uses local default

Premium covers transparently extend base functionality without code changes.
"""

import requests
import os
import secrets
import ipaddress
from typing import Optional, Tuple
from urllib.parse import urlparse
import logging
import socket
import io
from PIL import Image

logger = logging.getLogger(__name__)


class CoverService:
    """Service for managing book covers with tiered priority."""

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
           - bookcover.longitood.com (Goodreads covers)
        2. Cover from source metadata (e.g., from Open Library/BN)
        3. Cover from Open Library by ISBN lookup
        4. Local default image

        Note: Biblioteka Narodowa doesn't provide covers. This method ensures
        covers always come from Open Library (or premium service if enabled).

        Args:
            isbn: ISBN number
            title: Book title
            author: Book author
            cover_from_source: Cover URL from metadata source (OL/BN)
            source_cover_data: Cover ID from Open Library (not used)

        Returns:
            Tuple of (cover_url, source) where source is:
            'open_library', 'premium_bookcover', 'local_default', or None
        """
        logger.info(f"CoverService: Getting cover for: {title or isbn}")

        def _is_placeholder(url: str) -> bool:
            """Return True if the URL points to a known "no cover" placeholder."""
            if not url:
                return False
            return 'no-cover' in url or '/no-cover' in url

        # 1. Try premium sources FIRST (if enabled and licensed)
        # Premium bookcover service has HIGHEST priority
        cover_url = CoverService._get_cover_from_premium_sources(isbn, title, author)
        if cover_url:
            logger.info(f"CoverService: Got premium cover from bookcover API")
            return cover_url, "premium_bookcover"

        # 2. Try cover from source metadata (Open Library or Biblioteka Narodowa)
        if cover_from_source:
            if _is_placeholder(cover_from_source):
                logger.info("CoverService: Metadata cover is placeholder, ignoring")
            else:
                logger.info(f"CoverService: Using cover from metadata source")
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
                'BookcoverService',
                'get_cover_from_bookcover_api',
                isbn=isbn,
                title=title,
                author=author
            )
            # Some premium responses indicate "no cover" by returning a
            # generic placeholder image.  We don't want to treat that as a
            # real cover because another source might have an actual image.
            if cover_url:
                # normalize case, but currently we care about the specific
                # cloudfront path used by bookcover API
                if 'no-cover.png' in cover_url:
                    logger.info(
                        "CoverService: Premium cover URL is placeholder, ignoring"
                    )
                    cover_url = None
                else:
                    logger.info("CoverService: Got premium cover from bookcover API")
                    return cover_url
        else:
            logger.info("CoverService: premium covers feature is not enabled")

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
        Download cover image from URL and save locally. Validate image with Pillow.

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

            # Re-validate final URL after redirects to prevent SSRF via redirects
            final_url = getattr(response, 'url', cover_url)
            if not CoverService._validate_url(final_url):
                logger.warning(f"CoverService: Final URL after redirects is not allowed: {final_url}")
                return None

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

            # Validate image content using Pillow
            try:
                img = Image.open(io.BytesIO(content))
                img.verify()  # will raise if not a valid image
            except Exception:
                logger.warning(f"CoverService: Downloaded content is not a valid image: {cover_url}")
                return None

            # Re-open image for safe processing (verify() may leave the file in unusable state)
            img = Image.open(io.BytesIO(content))
            img_format = (img.format or '').upper()
            ext_map = {'JPEG': '.jpg', 'JPG': '.jpg', 'PNG': '.png', 'GIF': '.gif'}

            # Determine file extension from image format or URL
            _, f_ext = os.path.splitext(urlparse(cover_url).path)
            if img_format in ext_map:
                f_ext = ext_map[img_format]

            if not f_ext or f_ext.lower() not in CoverService.ALLOWED_EXTENSIONS:
                f_ext = '.jpg'

            # Random filename
            random_hex = secrets.token_hex(8)
            filename = random_hex + f_ext
            filepath = os.path.join(upload_folder, filename)

            # Save sanitized image (re-encode to strip metadata for JPEG/PNG)
            try:
                if img_format == 'GIF':
                    # Preserve GIF bytes (animation)
                    with open(filepath, 'wb') as f:
                        f.write(content)
                else:
                    # Convert to RGB for JPEG to avoid alpha channel issues
                    save_format = 'PNG' if f_ext == '.png' else 'JPEG'
                    if save_format == 'JPEG':
                        img = img.convert('RGB')
                    img.save(filepath, format=save_format, optimize=True, quality=85)
            except Exception as e:
                logger.error(f"CoverService: Save error while re-encoding image: {e}")
                return None

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

        Adds DNS resolution: any resolved IP that is private/loopback will be rejected.

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
            try:
                # If hostname is an IP literal, check it directly
                ip = ipaddress.ip_address(parsed_url.hostname)
                if ip.is_private or ip.is_loopback:
                    return False
            except (ValueError, TypeError):
                # Hostname is not an IP literal -> resolve DNS and check returned addresses
                try:
                    infos = socket.getaddrinfo(parsed_url.hostname, None)
                    for info in infos:
                        sockaddr = info[4]
                        host_ip = sockaddr[0]
                        try:
                            ip = ipaddress.ip_address(host_ip)
                            if ip.is_private or ip.is_loopback:
                                return False
                        except Exception:
                            # ignore non-IP results
                            continue
                except socket.gaierror:
                    # DNS resolution failed - conservatively allow (don't block legitimate public hosts)
                    pass

            return True

        except Exception:
            return False
