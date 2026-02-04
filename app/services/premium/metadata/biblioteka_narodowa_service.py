"""
Biblioteka Narodowa (Polish National Library) metadata service.

Provides book metadata from the National Library of Poland API.
Documentation: https://data.bn.org.pl/docs/bibs

Priority: If enabled, BN data takes priority over Open Library.
Fallback: If book not found in BN, falls back to Open Library.

Note: BN API doesn't provide cover images - covers always come from Open Library
(or premium bookcover service if enabled).
"""

import requests
from typing import Optional, Dict, List
import logging
import re

logger = logging.getLogger(__name__)


class BibliotekaNarodowaService:
    """Service for querying Polish National Library API."""

    # API Configuration
    API_BASE_URL = "https://data.bn.org.pl/api/institutions/bibs.json"
    TIMEOUT = 10
    USER_AGENT = "Libriya/1.0 (Book Management System)"

    # Mapping from BN categories/types to application genres
    BN_TYPE_TO_GENRE_MAPPING = {
        # Fiction
        'beletrystyka': 'Fiction',
        'powieść': 'Fiction',
        'opowiadanie': 'Fiction',
        'utwór literacki': 'Fiction',
        'literatura artystyczna': 'Fiction',

        # Fantasy/Science Fiction
        'fantastyka': 'Fantasy',
        'science fiction': 'Fiction',

        # Romance
        'romans': 'Romance / Contemporary',

        # Crime/Thriller
        'kryminał': 'Crime / Thriller',
        'thriller': 'Crime / Thriller',

        # Young Adult/Children
        'literatura dziecięca': 'Children',
        'literatura młodzieżowa': 'Young Adult',

        # Drama/Poetry
        'drama': 'Poetry / Drama',
        'dramat': 'Poetry / Drama',
        'poemat': 'Poetry / Drama',
        'wiersze': 'Poetry / Drama',
        'poezja': 'Poetry / Drama',

        # Non-fiction - General
        'poradnik': 'Business / Self-Help',
        'podręcznik': 'Manual / Education',
        'przewodnik': 'Guide / Hobby',

        # Non-fiction - Educational/Academic
        'publikacja naukowa': 'Scientific / Academic',
        'monografia': 'Scientific / Academic',
        'akademicka': 'Scientific / Academic',

        # Non-fiction - Reference
        'słownik': 'Manual / Education',
        'encyklopedia': 'Manual / Education',

        # Non-fiction - Biography/Memoir
        'biografia': 'Non-fiction',
        'autobiografia': 'Non-fiction',
        'wspomnienia': 'Non-fiction',

        # Non-fiction - Art/Culture
        'sztuka': 'Culture / Art',
        'historia': 'Non-fiction',
        'archeologia': 'Non-fiction',

        # Non-fiction - Science
        'nauka': 'Scientific / Academic',
        'przyrodoznawstwo': 'Scientific / Academic',

        # Other
        'publicystyka': 'Non-fiction',
        'esej': 'Non-fiction',
    }

    @staticmethod
    def search_by_isbn(isbn: str) -> Optional[Dict]:
        """
        Search for book in Biblioteka Narodowa by ISBN.

        Args:
            isbn: ISBN-13 or ISBN-10 (will be normalized)

        Returns:
            Dict with book data if found, None otherwise.
            Format:
            {
                'isbn': '9788375799538',
                'title': 'Book Title',
                'authors': ['Author Name'],
                'year': 2023,
                'publisher': 'Publisher Name',
                'genres': ['Fiction', 'Crime / Thriller'],
                'source': 'biblioteka_narodowa',
                'bn_id': '123456789'  # BN internal ID
            }
        """
        if not isbn:
            logger.warning("BibliotekaNarodowaService: ISBN is empty")
            return None

        # Normalize ISBN - remove hyphens/spaces
        clean_isbn = isbn.replace("-", "").replace(" ", "").strip()

        logger.info(f"BibliotekaNarodowaService: Searching for ISBN: {clean_isbn}")

        try:
            # Query BN API with ISBN or ISSN parameter
            params = {"isbnIssn": clean_isbn}
            response = requests.get(
                BibliotekaNarodowaService.API_BASE_URL,
                params=params,
                timeout=BibliotekaNarodowaService.TIMEOUT,
                headers={"User-Agent": BibliotekaNarodowaService.USER_AGENT},
            )

            response.raise_for_status()
            data = response.json()

            logger.debug(f"BibliotekaNarodowaService: API response received for {clean_isbn}")

            # BN API returns dict with 'bibs' array containing results
            if not isinstance(data, dict) or not data.get('bibs'):
                logger.info(f"BibliotekaNarodowaService: No results for ISBN {clean_isbn}")
                return None

            bibs = data.get('bibs', [])
            if len(bibs) == 0:
                logger.info(f"BibliotekaNarodowaService: No bibs in response for ISBN {clean_isbn}")
                return None

            # Take first result
            bib_record = bibs[0]

            # Parse the response
            book_data = BibliotekaNarodowaService._parse_bib_record(bib_record, clean_isbn)

            if book_data:
                logger.info(
                    f"BibliotekaNarodowaService: Found book in BN: {book_data.get('title')}"
                )
                return book_data

            return None

        except requests.RequestException as e:
            logger.error(f"BibliotekaNarodowaService: API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"BibliotekaNarodowaService: Error parsing response: {e}")
            return None

    @staticmethod
    def _parse_bib_record(record: Dict, isbn: str) -> Optional[Dict]:
        """
        Parse BN API response record into unified book format.
        Uses MARC data for cleaner extraction.

        Args:
            record: Single bibliographic record from BN API
            isbn: ISBN used for search

        Returns:
            Unified book data dict or None if essential fields missing
        """
        try:
            # Use MARC data if available, otherwise fallback to simple fields
            marc_data = record.get("marc", {})
            fields = marc_data.get("fields", []) if marc_data else []

            # Extract from MARC or fallback to simple fields
            title = BibliotekaNarodowaService._extract_title_from_marc(fields) or record.get("title")
            if not title:
                logger.warning("BibliotekaNarodowaService: Record missing title")
                return None

            authors = BibliotekaNarodowaService._extract_authors_from_marc(fields)
            year = BibliotekaNarodowaService._extract_year_from_marc(
                fields) or BibliotekaNarodowaService._extract_year(record)
            publisher = BibliotekaNarodowaService._extract_publisher_from_marc(
                fields) or BibliotekaNarodowaService._extract_publisher(record)
            genres = BibliotekaNarodowaService._extract_genres(record)
            bn_id = record.get("id", record.get("identifier", ""))

            book_data = {
                "isbn": isbn,
                "title": title,
                "authors": authors,
                "year": year,
                "publisher": publisher,
                "genres": genres if genres else [],
                "source": "biblioteka_narodowa",
                "bn_id": bn_id,
            }

            return book_data

        except Exception as e:
            logger.error(f"BibliotekaNarodowaService: Error parsing record: {e}")
            return None

    @staticmethod
    def _extract_title_from_marc(fields: List[Dict]) -> Optional[str]:
        """Extract title from MARC field 245."""
        try:
            for field_dict in fields:
                # Field 245 contains title
                field_245 = field_dict.get("245")
                if field_245:
                    subfields = field_245.get("subfields", [])
                    title_parts = []

                    # Subfield 'a' - main title
                    # Subfield 'b' - remainder of title
                    for subfield in subfields:
                        if isinstance(subfield, dict):
                            if 'a' in subfield:
                                title_parts.append(subfield['a'].rstrip('/:; '))
                            elif 'b' in subfield:
                                title_parts.append(subfield['b'].rstrip('/:; '))

                    if title_parts:
                        title = ' : '.join(title_parts)
                        # Clean up
                        title = re.sub(r'\s+', ' ', title).strip()
                        return title

            return None
        except Exception as e:
            logger.warning(f"BibliotekaNarodowaService: Error extracting title from MARC: {e}")
            return None

    @staticmethod
    def _extract_authors_from_marc(fields: List[Dict]) -> List[str]:
        """Extract authors from MARC fields 100 and 700."""
        try:
            authors = []

            for field_dict in fields:
                # Field 100 - main author
                field_100 = field_dict.get("100")
                if field_100:
                    author = BibliotekaNarodowaService._parse_author_field(field_100)
                    if author:
                        authors.append(author)

                # Field 700 - additional authors
                field_700 = field_dict.get("700")
                if field_700:
                    author = BibliotekaNarodowaService._parse_author_field(field_700)
                    if author:
                        authors.append(author)

            return authors[:3]  # Return max 3 authors

        except Exception as e:
            logger.warning(f"BibliotekaNarodowaService: Error extracting authors from MARC: {e}")
            return []

    @staticmethod
    def _parse_author_field(field: Dict) -> Optional[str]:
        """Parse author from MARC 100 or 700 field."""
        try:
            subfields = field.get("subfields", [])
            author_parts = []

            for subfield in subfields:
                if isinstance(subfield, dict):
                    # 'a' - surname, given names
                    # 'd' - dates (ignore)
                    # 'e' - relationship (ignore)
                    if 'a' in subfield:
                        name = subfield['a'].rstrip(',. ')
                        author_parts.append(name)

            if author_parts:
                # Combine parts and format nicely
                author = ' '.join(author_parts)
                # Remove trailing dates in parentheses
                author = re.sub(r'\s*\([^)]*\)\s*$', '', author).strip()

                # Convert "LastName, FirstName" to "FirstName LastName"
                if ',' in author:
                    parts = [p.strip() for p in author.split(',')]
                    if len(parts) == 2:
                        author = f"{parts[1]} {parts[0]}"

                return author if len(author) > 2 else None

            return None
        except Exception as e:
            logger.warning(f"BibliotekaNarodowaService: Error parsing author field: {e}")
            return None

    @staticmethod
    def _extract_year_from_marc(fields: List[Dict]) -> Optional[int]:
        """Extract publication year from MARC field 260 or 008."""
        try:
            for field_dict in fields:
                # Field 260 - Publication info
                field_260 = field_dict.get("260")
                if field_260:
                    subfields = field_260.get("subfields", [])
                    for subfield in subfields:
                        if isinstance(subfield, dict) and 'c' in subfield:
                            # Subfield 'c' contains date
                            date_str = subfield['c']
                            year_match = re.search(r"\d{4}", str(date_str))
                            if year_match:
                                return int(year_match.group())

            return None
        except Exception as e:
            logger.warning(f"BibliotekaNarodowaService: Error extracting year from MARC: {e}")
            return None

    @staticmethod
    def _extract_publisher_from_marc(fields: List[Dict]) -> Optional[str]:
        """Extract publisher from MARC field 260."""
        try:
            for field_dict in fields:
                # Field 260 - Publication, distribution, etc.
                field_260 = field_dict.get("260")
                if field_260:
                    subfields = field_260.get("subfields", [])
                    for subfield in subfields:
                        if isinstance(subfield, dict) and 'b' in subfield:
                            # Subfield 'b' contains publisher
                            publisher = subfield['b'].rstrip('., ')
                            if publisher:
                                return publisher

            return None
        except Exception as e:
            logger.warning(f"BibliotekaNarodowaService: Error extracting publisher from MARC: {e}")
            return None

    @staticmethod
    def _extract_authors(record: Dict) -> List[str]:
        """Extract author names from BN record."""
        try:
            authors = []

            # BN API provides author info in 'author' field
            # Format: "LastName, FirstName (birth) LastName, FirstName... Wydawnictwo..."
            author_field = record.get("author", "")

            if author_field:
                # Remove publisher info (usually at end)
                author_field = re.sub(r'\s*Wydawnictwo.*$', '', author_field, flags=re.IGNORECASE)

                # Split by "LastName, FirstName" patterns
                author_parts = re.split(r'\s+(?=[A-Z][a-ząćęłńóśźż]+,)', author_field)

                for part in author_parts:
                    if part.strip() and part.strip() not in ['a', 'i']:
                        # Clean up parenthetical info (birth dates, etc)
                        clean = re.sub(r'\s*\([^)]*\)\s*', ' ', part.strip())
                        # Remove extra spaces
                        clean = re.sub(r'\s+', ' ', clean).strip()
                        if clean and len(clean) > 2:
                            authors.append(clean)

            return authors[:3]  # Return max 3 authors

        except Exception as e:
            logger.warning(f"BibliotekaNarodowaService: Error extracting authors: {e}")
            return []

    @staticmethod
    def _extract_year(record: Dict) -> Optional[int]:
        """Extract publication year from BN record."""
        try:
            # BN API uses 'publicationYear', but let's also check other fields
            year_str = (record.get("publicationYear")
                        or record.get("date")
                        or record.get("timePeriodOfCreation")
                        or record.get("issued")
                        or record.get("dateIssued"))

            if year_str:
                # Extract first 4 digit sequence as year
                year_match = re.search(r"\d{4}", str(year_str))
                if year_match:
                    return int(year_match.group())

            return None

        except Exception as e:
            logger.warning(f"BibliotekaNarodowaService: Error extracting year: {e}")
            return None

    @staticmethod
    def _extract_publisher(record: Dict) -> Optional[str]:
        """Extract publisher name from BN record."""
        try:
            # BN API uses 'publisher' field
            publisher = record.get("publisher")

            if isinstance(publisher, list):
                publisher = publisher[0] if publisher else None

            if publisher:
                # Clean up - remove trailing commas and duplicates
                publisher = re.sub(r',\s*$', '', publisher.strip())
                publisher = re.sub(r',\s*[A-Z][a-z]+,', ',', publisher)  # Remove duplicate publisher
                # Take first part (before comma usually)
                if ',' in publisher:
                    publisher = publisher.split(',')[0].strip()
                return publisher if publisher else None

            return None

        except Exception as e:
            logger.warning(f"BibliotekaNarodowaService: Error extracting publisher: {e}")
            return None

    @staticmethod
    def _extract_genres(record: Dict) -> List[str]:
        """
        Extract genres from BN record and map to app genres.

        BN provides type/category information that we map to app genres.
        Uses simple fields, MARC field 380 (form of work), and MARC field 655 (genre/form).
        """
        try:
            genres = set()

            # BN API uses 'genre', 'formOfWork', 'domain', 'kind'
            genre_field = record.get("genre", "")
            form_field = record.get("formOfWork", "")
            domain_field = record.get("domain", "")
            kind_field = record.get("kind", "")

            all_types = []

            for field in [genre_field, form_field, domain_field, kind_field]:
                if isinstance(field, str) and field.strip():
                    # Split by space or comma
                    parts = re.split(r'[\s,]+', field.lower())
                    all_types.extend([p.strip() for p in parts if p.strip() and len(p.strip()) > 1])
                elif isinstance(field, list):
                    all_types.extend([t.lower().strip() for t in field if isinstance(t, str) and t.strip()])

            # Also extract from MARC fields
            marc_data = record.get("marc", {})
            marc_fields = marc_data.get("fields", []) if marc_data else []

            for field_dict in marc_fields:
                # Field 380 - form of work
                field_380 = field_dict.get("380")
                if field_380:
                    subfields = field_380.get("subfields", [])
                    for subfield in subfields:
                        if isinstance(subfield, dict) and 'a' in subfield:
                            text = subfield['a'].lower().strip().rstrip('.,')
                            if text and len(text) > 1:
                                all_types.append(text)

                # Field 655 - form/genre (primary genre field)
                field_655 = field_dict.get("655")
                if field_655:
                    subfields = field_655.get("subfields", [])
                    for subfield in subfields:
                        if isinstance(subfield, dict) and 'a' in subfield:
                            text = subfield['a'].lower().strip().rstrip('.,')
                            if text and len(text) > 1:
                                all_types.append(text)

            # Map BN types to app genres
            for bn_type in all_types:
                # Direct mapping
                if bn_type in BibliotekaNarodowaService.BN_TYPE_TO_GENRE_MAPPING:
                    genre = BibliotekaNarodowaService.BN_TYPE_TO_GENRE_MAPPING[bn_type]
                    genres.add(genre)
                else:
                    # Substring matching
                    for bn_key, app_genre in BibliotekaNarodowaService.BN_TYPE_TO_GENRE_MAPPING.items():
                        if bn_key in bn_type or bn_type in bn_key:
                            genres.add(app_genre)
                            break

            # If no genres found, try to infer from subject
            if not genres:
                subject = record.get("subject", "").lower()
                if "psychologia" in subject or "samopomoc" in subject or "kontrola" in subject:
                    genres.add("Business / Self-Help")
                elif "literatura" in subject or "fiction" in subject:
                    genres.add("Fiction")
                elif "historia" in subject:
                    genres.add("Non-fiction")

            return list(genres)

        except Exception as e:
            logger.warning(f"BibliotekaNarodowaService: Error extracting genres: {e}")
            return []
