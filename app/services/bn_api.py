"""
Biblioteka Narodowa (Polish National Library) API client.

Integration with BN API for searching books in Polish national library catalogs.
Documentation: https://data.bn.org.pl/docs/bibs
"""

import requests
from typing import List, Dict, Optional, Tuple
from app.services.isbn_validator import ISBNValidator
import logging

logger = logging.getLogger(__name__)


class BNAPIClient:
    """Client for Biblioteka Narodowa API."""

    # API endpoints
    BN_DIRECT_URL = "https://data.bn.org.pl/api/institutions/bibs.json"
    BN_NETWORKS_URL = "https://data.bn.org.pl/api/networks/bibs.json"

    # Timeouts
    TIMEOUT = 15

    @staticmethod
    def search_by_isbn(isbn: str) -> Optional[Dict]:
        """
        Search for book by ISBN in BN catalogs.

        Tries both direct BN catalog and combined catalogs.

        Args:
            isbn: ISBN number (10 or 13 digits, with or without formatting)

        Returns:
            Book data dict or None if not found
        """
        normalized_isbn = ISBNValidator.normalize(isbn)

        logger.info(f"BN: Searching by ISBN: {normalized_isbn}")

        # Try combined catalogs first (more comprehensive)
        result = BNAPIClient._search_by_isbn_in_catalog(
            BNAPIClient.BN_NETWORKS_URL,
            normalized_isbn
        )
        if result:
            return result

        # Fallback to direct BN catalog
        result = BNAPIClient._search_by_isbn_in_catalog(
            BNAPIClient.BN_DIRECT_URL,
            normalized_isbn
        )

        return result

    @staticmethod
    def _search_by_isbn_in_catalog(
        catalog_url: str,
        isbn: str,
        limit: int = 5
    ) -> Optional[Dict]:
        """
        Search in specific BN catalog.

        Args:
            catalog_url: URL of BN catalog
            isbn: Normalized ISBN
            limit: Max results to return

        Returns:
            Newest matching book or None
        """
        try:
            params = {
                "isbnIssn": isbn,
                "limit": limit
            }

            response = requests.get(
                catalog_url,
                params=params,
                timeout=BNAPIClient.TIMEOUT
            )
            response.raise_for_status()

            data = response.json()
            bibs = data.get("bibs", [])

            if bibs:
                # Select newest record by createdDate (most complete metadata)
                newest_record = BNAPIClient._get_newest_record(bibs)
                return BNAPIClient._parse_bn_record(newest_record)

            return None

        except requests.exceptions.Timeout:
            logger.warning(f"BN timeout for ISBN: {isbn}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"BN API error for ISBN {isbn}: {e}")
            return None
        except Exception as e:
            logger.error(f"BN parsing error: {e}")
            return None

    @staticmethod
    def _get_newest_record(records: List[Dict]) -> Dict:
        """
        Select newest record from list based on createdDate.

        Args:
            records: List of BN records

        Returns:
            Newest record (most recent createdDate)
        """
        if not records:
            return {}

        from datetime import datetime

        def get_created_date(record):
            created = record.get('createdDate', '')
            if created:
                try:
                    return datetime.fromisoformat(created.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    return datetime.min
            return datetime.min

        return max(records, key=get_created_date)

    @staticmethod
    def search_by_title(
        title: str,
        author: Optional[str] = None,
        limit: int = 10,
        use_networks: bool = True
    ) -> List[Dict]:
        """
        Search for books by title (and optionally author) in BN.

        Args:
            title: Book title (min 3 characters)
            author: Author name (optional)
            limit: Max results (max 100)
            use_networks: Use combined catalogs or direct BN

        Returns:
            List of book data dicts
        """
        if not title or len(title.strip()) < 3:
            return []

        logger.info(f"BN: Searching by title: '{title}', author: '{author}'")

        catalog_url = BNAPIClient.BN_NETWORKS_URL if use_networks else BNAPIClient.BN_DIRECT_URL

        try:
            params = {
                "title": title,
                "limit": min(limit, 100)  # Max 100 per API
            }

            if author:
                params["author"] = author

            response = requests.get(
                catalog_url,
                params=params,
                timeout=BNAPIClient.TIMEOUT
            )
            response.raise_for_status()

            data = response.json()
            bibs = data.get("bibs", [])

            results = []
            for bib in bibs[:limit]:
                parsed = BNAPIClient._parse_bn_record(bib)
                if parsed:
                    results.append(parsed)

            logger.info(f"BN: Found {len(results)} results")
            return results

        except requests.exceptions.Timeout:
            logger.warning(f"BN timeout for title: {title}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"BN API error for title '{title}': {e}")
            return []
        except Exception as e:
            logger.error(f"BN parsing error: {e}")
            return []

    @staticmethod
    def _parse_bn_record(record: Dict) -> Optional[Dict]:
        """
        Parse BN API record into standardized format.

        Extracts data from top-level fields first, then fills gaps from MARC record.

        Args:
            record: Raw BN record dict

        Returns:
            Standardized book data dict
        """
        try:
            import re

            # Extract basic fields from top-level
            title = record.get("title", "").strip()
            author = record.get("author", "").strip()
            isbn = record.get("isbnIssn", "").strip()
            publisher = record.get("publisher", "").strip()
            year = record.get("publicationYear", "").strip()
            language = record.get("language", "").strip()
            bn_id = record.get("id")

            # Try to extract missing data from MARC record
            marc = record.get("marc", {})
            if marc and isinstance(marc, dict):
                fields = marc.get("fields", [])

                # Look for author in MARC field 245$c (author statement of responsibility)
                # Prefer MARC if top-level author contains parentheses (extra metadata)
                marc_author = None
                for field in fields:
                    if isinstance(field, dict) and "245" in field:
                        subfields = field["245"].get("subfields", [])
                        for subfield in subfields:
                            if isinstance(subfield, dict) and "c" in subfield:
                                author_text = subfield["c"].strip()
                                # Remove trailing punctuation
                                author_text = re.sub(r'[.,;:\s]*$', '', author_text)
                                if author_text:
                                    marc_author = author_text
                                break

                # Use MARC author if top-level has too much metadata (parentheses)
                if marc_author and ('(' in author or ')' in author):
                    author = marc_author
                elif not author and marc_author:
                    author = marc_author

                # Look for publication year in MARC field 260$c or 264$c
                if not year or year.isspace():
                    for field in fields:
                        if isinstance(field, dict):
                            for field_code in ["260", "264"]:
                                if field_code in field:
                                    subfields = field[field_code].get("subfields", [])
                                    for subfield in subfields:
                                        if isinstance(subfield, dict) and "c" in subfield:
                                            year_text = subfield["c"].strip()
                                            # Extract 4-digit year
                                            year_match = re.search(r'\b(\d{4})\b', year_text)
                                            if year_match:
                                                year = year_match.group(1)
                                                break
                                    if year and not year.isspace():
                                        break

                # Look for publisher in MARC field 260$b or 264$b
                if not publisher:
                    for field in fields:
                        if isinstance(field, dict):
                            for field_code in ["260", "264"]:
                                if field_code in field:
                                    subfields = field[field_code].get("subfields", [])
                                    for subfield in subfields:
                                        if isinstance(subfield, dict) and "b" in subfield:
                                            pub_text = subfield["b"].strip()
                                            # Remove trailing punctuation
                                            pub_text = re.sub(r'[.,;:\s]*$', '', pub_text)
                                            if pub_text:
                                                publisher = pub_text
                                            break
                                    if publisher:
                                        break

            # Clean up publisher name
            if publisher:
                publisher = re.sub(r'[.,;:\s]*$', '', publisher.strip())

            # Parse author (format: "Sacher-Masoch, Leopold von (1836-1895)")
            author_names = []
            if author:
                # Split multiple authors if they exist
                for a in author.split("|"):
                    a = a.strip()
                    if a:
                        # Remove dates and extra info in parentheses
                        cleaned = re.sub(r'\s*\([^)]*\).*$', '', a)
                        author_names.append(cleaned.strip())

            # Clean up title: remove trailing "/" and whitespace
            if title:
                title = re.sub(r'[\s/]*$', '', title.strip())

            if not title:
                return None

            return {
                "source": "bn_networks",  # or "bn_direct"
                "source_id": bn_id,
                "title": title,
                "authors": author_names,
                "isbn": isbn if isbn else None,
                "publisher": publisher if publisher else None,
                "year": int(year) if year and year.isdigit() else None,
                "language": language,
                "cover": None,  # BN doesn't provide covers
                "marc_record": marc,  # Full MARC if available
            }

        except Exception as e:
            logger.error(f"Error parsing BN record: {e}")
            return None
