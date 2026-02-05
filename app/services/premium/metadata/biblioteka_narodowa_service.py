"""
Biblioteka Narodowa (Polish National Library) metadata service.
Updated with Authority ID Mapping for precise genre classification.
Comments translated to English.
"""

import requests
from typing import Optional, Dict, List
import logging
import re
import json
import os

logger = logging.getLogger(__name__)


class BibliotekaNarodowaService:
    """Service for querying Polish National Library API with ID-based mapping."""

    # API Configuration
    API_BASE_URL = "https://data.bn.org.pl/api/institutions/bibs.json"
    TIMEOUT = 10
    USER_AGENT = "Libriya/1.0 (Book Management System)"

    @staticmethod
    def get_genres_list():
        """Dynamically fetch genre names from the database."""
        from app.models import Genre
        from app import db
        genres = db.session.query(Genre).order_by(Genre.id).all()
        return [g.name for g in genres]

    # Legacy text dictionary (used as fallback only)
    BN_TYPE_TO_GENRE_MAPPING = {
        'beletrystyka': 'Fiction', 'powieść': 'Fiction', 'opowiadanie': 'Fiction',
        'fantastyka': 'Fantasy', 'science fiction': 'Fiction',
        'romans': 'Romance / Contemporary', 'kryminał': 'Crime / Thriller',
        'thriller': 'Crime / Thriller', 'literatura dziecięca': 'Children',
        'literatura młodzieżowa': 'Young Adult', 'poezja': 'Poetry / Drama',
        'poradnik': 'Business / Self-Help', 'podręcznik': 'Manual / Education',
        'słownik': 'Manual / Education', 'biografia': 'Non-fiction',
        'sztuka': 'Culture / Art', 'historia': 'Non-fiction'
    }

    _id_map_cache = None

    @classmethod
    def _get_id_map(cls) -> Dict[str, int]:
        """Loads the mapping of 6466 BN Authority IDs (Singleton)."""
        if cls._id_map_cache is None:
            # Path to the JSON file in the data folder next to the service
            path = os.path.join(os.path.dirname(__file__), 'bn_id_to_internal_id.json')
            try:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        cls._id_map_cache = json.load(f)
                    logger.info(f"BN Service: Loaded {len(cls._id_map_cache)} authority mappings.")
                else:
                    logger.warning(f"BN Service: Mapping file not found at {path}")
                    cls._id_map_cache = {}
            except Exception as e:
                logger.error(f"BN Service: Failed to load mapping: {e}")
                cls._id_map_cache = {}
        return cls._id_map_cache

    @staticmethod
    def search_by_isbn(isbn: str) -> Optional[Dict]:
        """Search for book in Biblioteka Narodowa by ISBN."""
        if not isbn:
            return None

        clean_isbn = isbn.replace("-", "").replace(" ", "").strip()
        logger.info(f"BN Service: Searching ISBN: {clean_isbn}")

        try:
            params = {"isbnIssn": clean_isbn}
            response = requests.get(
                BibliotekaNarodowaService.API_BASE_URL,
                params=params,
                timeout=BibliotekaNarodowaService.TIMEOUT,
                headers={"User-Agent": BibliotekaNarodowaService.USER_AGENT},
            )
            response.raise_for_status()
            data = response.json()

            bibs = data.get('bibs', [])
            if not bibs:
                return None

            # Parse the first result
            return BibliotekaNarodowaService._parse_bib_record(bibs[0], clean_isbn)

        except Exception as e:
            logger.error(f"BN Service: API error: {e}")
            return None

    @staticmethod
    def _parse_bib_record(record: Dict, isbn: str) -> Optional[Dict]:
        """Parse BN record into unified book format."""
        try:
            marc_data = record.get("marc", {})
            fields = marc_data.get("fields", []) if marc_data else []

            title = BibliotekaNarodowaService._extract_title_from_marc(fields) or record.get("title")
            if not title:
                return None

            book_data = {
                "isbn": isbn,
                "title": title,
                "authors": BibliotekaNarodowaService._extract_authors_from_marc(fields),
                "year": BibliotekaNarodowaService._extract_year_from_marc(fields)
                or BibliotekaNarodowaService._extract_year(record),
                "publisher": BibliotekaNarodowaService._extract_publisher_from_marc(fields)
                or BibliotekaNarodowaService._extract_publisher(record),
                "genres": BibliotekaNarodowaService._extract_genres(record),
                "source": "biblioteka_narodowa",
                "bn_id": record.get("id", record.get("identifier", "")),
            }
            return book_data
        except Exception as e:
            logger.error(f"BN Service: Parsing error: {e}")
            return None

    @staticmethod
    def _extract_genres(record: Dict) -> List[str]:
        """
        Primary Genre Extraction using Authority IDs and fallback text matching.
        """
        genres = set()
        id_map = BibliotekaNarodowaService._get_id_map()

        marc_data = record.get("marc", {})
        fields = marc_data.get("fields", [])

        # 1. SEARCH BY ID (Authority Mapping)
        # Checking MARC tags 380, 655, and 650 for known Authority IDs
        target_tags = ['380', '655', '650']
        for field_dict in fields:
            for tag in target_tags:
                if tag in field_dict:
                    subfields = field_dict[tag].get("subfields", [])
                    for sub in subfields:
                        # Extract subfield values (e.g., 'a' or '1')
                        for val in sub.values():
                            clean_val = str(val).strip().rstrip('.')
                            if clean_val in id_map:
                                genre_idx = id_map[clean_val] - 1
                                genres_list = BibliotekaNarodowaService.get_genres_list()
                                if 0 <= genre_idx < len(genres_list):
                                    genres.add(genres_list[genre_idx])

        # If a precise match by ID is found, return early
        if genres:
            return list(genres)

        # 2. FALLBACK (Keyword-based text matching)
        genre_field = str(record.get("genre", "")).lower()
        form_field = str(record.get("formOfWork", "")).lower()

        all_text = f"{genre_field} {form_field}"
        for bn_key, app_genre in BibliotekaNarodowaService.BN_TYPE_TO_GENRE_MAPPING.items():
            if bn_key in all_text:
                genres.add(app_genre)

        return list(genres) if genres else ["Others"]

    # --- MARC HELPER METHODS (TITLE, AUTHORS, ETC) ---

    @staticmethod
    def _extract_title_from_marc(fields: List[Dict]) -> Optional[str]:
        """Extract title from MARC field 245."""
        for f in fields:
            if "245" in f:
                subs = f["245"].get("subfields", [])
                parts = [list(s.values())[0] for s in subs if 'a' in s or 'b' in s]
                return " ".join(parts).rstrip('/:; ').strip() if parts else None
        return None

    @staticmethod
    def _extract_authors_from_marc(fields: List[Dict]) -> List[str]:
        """Extract primary and additional authors from MARC fields 100 and 700."""
        authors = []
        for f in fields:
            for tag in ["100", "700"]:
                if tag in f:
                    subs = f[tag].get("subfields", [])
                    name_parts = [s['a'] for s in subs if 'a' in s]
                    if name_parts:
                        name = name_parts[0].rstrip(',. ')
                        if ',' in name:
                            p = name.split(',')
                            name = f"{p[1].strip()} {p[0].strip()}"
                        authors.append(name)
        return list(dict.fromkeys(authors))[:3]

    @staticmethod
    def _extract_year_from_marc(fields: List[Dict]) -> Optional[int]:
        """Extract publication year from MARC field 260 or 264."""
        for f in fields:
            if "260" in f or "264" in f:
                tag = "260" if "260" in f else "264"
                subs = f[tag].get("subfields", [])
                for s in subs:
                    if 'c' in s:
                        match = re.search(r"\d{4}", str(s['c']))
                        if match:
                            return int(match.group())
        return None

    @staticmethod
    def _extract_publisher_from_marc(fields: List[Dict]) -> Optional[str]:
        """Extract publisher from MARC field 260 or 264."""
        for f in fields:
            if "260" in f or "264" in f:
                tag = "260" if "260" in f else "264"
                subs = f[tag].get("subfields", [])
                for s in subs:
                    if 'b' in s:
                        return str(s['b']).rstrip('., ')
        return None

    @staticmethod
    def _extract_year(record: Dict) -> Optional[int]:
        """Fallback method to extract year from simple fields."""
        y = record.get("publicationYear") or record.get("date")
        if y:
            m = re.search(r"\d{4}", str(y))
            if m:
                return int(m.group())
        return None

    @staticmethod
    def _extract_publisher(record: Dict) -> Optional[str]:
        """Fallback method to extract publisher from simple fields."""
        p = record.get("publisher")
        if isinstance(p, list) and p:
            p = p[0]
        return str(p).split(',')[0].strip() if p else None
