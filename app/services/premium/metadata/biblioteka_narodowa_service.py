import requests
from typing import Optional, Dict, List
import logging
import re
import json
import os

logger = logging.getLogger(__name__)


class BibliotekaNarodowaService:
    """
    Final Libriya Metadata Service.
    Deterministic classification using MARC-rich data from BN API.
    """

    API_BASE_URL = "https://data.bn.org.pl/api/institutions/bibs.json"
    TIMEOUT = 10
    USER_AGENT = "Libriya/1.0 (Book Management System)"

    # Memory caches
    _ukd_map_cache = None
    _id_map_cache = None
    _genres_names_cache = None

    @classmethod
    def get_genres_list(cls) -> List[str]:
        """Dynamically fetch and cache genre names from the database."""
        if cls._genres_names_cache is None:
            try:
                from app.models import Genre
                from app import db
                # Order by ID is crucial for index-based mapping
                genres = db.session.query(Genre).order_by(Genre.id).all()
                cls._genres_names_cache = [g.name for g in genres]
                logger.info(f"BN Service: Synced {len(cls._genres_names_cache)} genres from DB.")
            except Exception as e:
                logger.error(f"BN Service: Database error: {e}")
                # Static fallback to prevent system crash
                return [
                    'Business / Self-Help', 'Children', 'Young Adult', 'Fantasy', 'Comic',
                    'Crime / Thriller', 'Culture / Art', 'Non-fiction', 'Fiction',
                    'Popular Science', 'Scientific / Academic', 'Poetry / Drama',
                    'Manual / Education', 'Guide / Hobby', 'Press',
                    'Religion / Philosophy', 'Romance / Contemporary', 'Others'
                ]
        return cls._genres_names_cache

    @classmethod
    def _get_ukd_map(cls) -> Dict[str, str]:
        """Loads UKD mapping from JSON file."""
        if cls._ukd_map_cache is None:
            path = os.path.join(os.path.dirname(__file__), 'ukd_mapping.json')
            try:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        cls._ukd_map_cache = json.load(f)
                else:
                    cls._ukd_map_cache = {}
            except Exception as e:
                logger.error(f"BN Service: Failed to load UKD map: {e}")
                cls._ukd_map_cache = {}
        return cls._ukd_map_cache

    @classmethod
    def _get_id_map(cls) -> Dict[str, int]:
        """Loads BN Authority ID to Internal ID mapping."""
        if cls._id_map_cache is None:
            path = os.path.join(os.path.dirname(__file__), 'bn_id_to_internal_id.json')
            try:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        cls._id_map_cache = json.load(f)
                else:
                    cls._id_map_cache = {}
            except Exception as e:
                logger.error(f"BN Service: Failed to load ID map: {e}")
                cls._id_map_cache = {}
        return cls._id_map_cache

    @staticmethod
    def search_by_isbn(isbn: str) -> Optional[Dict]:
        """Search BN for a book and return parsed Libriya metadata."""
        if not isbn:
            return None
        clean_isbn = isbn.replace("-", "").replace(" ", "").strip()

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
            return BibliotekaNarodowaService._parse_bib_record(bibs[0], clean_isbn)
        except Exception as e:
            logger.error(f"BN Service: API connection error: {e}")
            return None

    @staticmethod
    def _parse_bib_record(record: Dict, isbn: str) -> Optional[Dict]:
        """Extracts core data using MARC fields if available."""
        marc_fields = record.get("marc", {}).get("fields", [])

        title = BibliotekaNarodowaService._extract_title_from_marc(marc_fields) or record.get("title")
        if not title:
            return None


        # Extract description from MARC 520, record['description'], or fallback to 'subject'
        description = None
        for f in marc_fields:
            if "520" in f:
                subs = f["520"].get("subfields", [])
                for s in subs:
                    if 'a' in s:
                        description = str(s['a']).strip()
                        break
                if description:
                    break
        if not description:
            description = record.get("description")
        if not description:
            description = record.get("subject")

        return {
            "isbn": isbn,
            "title": title,
            "authors": BibliotekaNarodowaService._extract_authors_from_marc(marc_fields),
            "year": BibliotekaNarodowaService._extract_year_from_marc(marc_fields) or record.get("publicationYear"),
            "publisher": BibliotekaNarodowaService._extract_publisher_from_marc(marc_fields) or record.get("publisher"),
            "genres": BibliotekaNarodowaService._extract_genres_with_priority(record, marc_fields),
            "description": description,
            "source": "biblioteka_narodowa",
            "bn_id": record.get("id"),
        }

    @staticmethod
    def _extract_genres_with_priority(record: Dict, fields: List[Dict]) -> List[str]:
        """Hierarchical classification logic: UKD > Authority IDs > Keywords."""
        genres = set()
        app_genres = BibliotekaNarodowaService.get_genres_list()

        # --- 1. UKD Mapping (Highest Reliability) ---
        ukd_map = BibliotekaNarodowaService._get_ukd_map()
        if ukd_map:
            # Specific prefixes first
            prefixes = sorted(ukd_map.keys(), key=len, reverse=True)
            for f in fields:
                if '080' in f:
                    for sub in f['080'].get("subfields", []):
                        if 'a' in sub:
                            code = str(sub['a']).strip()
                            for p in prefixes:
                                if code.startswith(p):
                                    genres.add(ukd_map[p])
                                    break

        if genres:
            return list(genres)

        # --- 2. Authority ID Mapping (6466 rules) ---
        id_map = BibliotekaNarodowaService._get_id_map()
        if id_map:
            for f in fields:
                for tag in ['380', '655', '650']:
                    if tag in f:
                        for sub in f[tag].get("subfields", []):
                            for val in sub.values():
                                clean_val = str(val).strip().rstrip('.')
                                if clean_val in id_map:
                                    idx = id_map[clean_val] - 1
                                    if 0 <= idx < len(app_genres):
                                        genres.add(app_genres[idx])

        if genres:
            return list(genres)

        # --- 3. Keyword Fallback ---
        meta = f"{record.get('genre', '')} {record.get('subject', '')}".lower()
        mapping = {
            'komiks': 'Comic', 'dzieci': 'Children', 'młodzież': 'Young Adult',
            'kryminał': 'Crime / Thriller', 'fantastyka': 'Fantasy', 'powieść': 'Fiction'
        }
        for key, val in mapping.items():
            if key in meta:
                genres.add(val)

        return list(genres) if genres else ["Others"]

    # --- MARC Helpers ---

    @staticmethod
    def _extract_title_from_marc(fields: List[Dict]) -> Optional[str]:
        for f in fields:
            if "245" in f:
                subs = f["245"].get("subfields", [])
                parts = [list(s.values())[0] for s in subs if 'a' in s or 'b' in s]
                return " ".join(parts).rstrip('/:; ').strip() if parts else None
        return None

    @staticmethod
    def _extract_authors_from_marc(fields: List[Dict]) -> List[str]:
        authors = []
        for f in fields:
            for tag in ["100", "700"]:
                if tag in f:
                    name = next(iter(f[tag].get("subfields", [{}])[0].values()), "")
                    if name:
                        authors.append(name.rstrip(',. '))
        return list(dict.fromkeys(authors))[:3]

    @staticmethod
    def _extract_year_from_marc(fields: List[Dict]) -> Optional[int]:
        for f in fields:
            for tag in ["260", "264"]:
                if tag in f:
                    for s in f[tag].get("subfields", []):
                        if 'c' in s:
                            m = re.search(r"\d{4}", str(s['c']))
                            if m:
                                return int(m.group())
        return None

    @staticmethod
    def _extract_publisher_from_marc(fields: List[Dict]) -> Optional[str]:
        for f in fields:
            for tag in ["260", "264"]:
                if tag in f:
                    for s in f[tag].get("subfields", []):
                        if 'b' in s:
                            return str(s['b']).rstrip('., ')
        return None
