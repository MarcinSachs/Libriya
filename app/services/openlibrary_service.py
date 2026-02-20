"""
Open Library API client.

Integration with Open Library API for searching books and covers.
Documentation: https://openlibrary.org/dev/docs/api/books
"""

import requests
from typing import List, Dict, Optional, Set
import logging
import re

logger = logging.getLogger(__name__)


# Mapping from Open Library subjects to application genres
# Mapped to actual genres in the database
OL_SUBJECT_TO_GENRE_MAPPING = {
    # Fiction related
    'fiction': 'Fiction',
    'science fiction': 'Fiction',
    'fantasy': 'Fantasy',
    'epic fantasy': 'Fantasy',
    'romantic fiction': 'Romance / Contemporary',
    'romance': 'Romance / Contemporary',
    'mystery': 'Crime / Thriller',
    'thriller': 'Crime / Thriller',
    'suspense': 'Crime / Thriller',
    'horror': 'Fiction',
    'gothic': 'Fiction',
    'western': 'Fiction',
    'crime': 'Crime / Thriller',
    'crime fiction': 'Crime / Thriller',
    'historical fiction': 'Fiction',
    'alternate history': 'Fiction',
    'dystopian': 'Fiction',
    'adventure': 'Fiction',
    'action': 'Fiction',
    'comedy': 'Fiction',
    'humorous fiction': 'Fiction',
    'contemporary fiction': 'Fiction',
    'literary': 'Fiction',
    'literary fiction': 'Fiction',
    'drama': 'Poetry / Drama',
    'family saga': 'Fiction',
    'graphic novel': 'Comic',
    'comic': 'Comic',
    'comics': 'Comic',
    'young adult fiction': 'Young Adult',
    'young adult': 'Young Adult',
    'new adult': 'Young Adult',
    'children\'s literature': 'Children',
    'children\'s fiction': 'Children',
    'picture books': 'Children',
    'fairy tales': 'Fiction',
    'fables': 'Fiction',
    'mythology': 'Fiction',
    'short stories': 'Fiction',
    'poetry': 'Poetry / Drama',

    # Non-fiction - Autobiography/Biography/Memoir
    'autobiography': 'Non-fiction',
    'biography': 'Non-fiction',
    'memoir': 'Non-fiction',
    'true story': 'Non-fiction',
    'true crime': 'Crime / Thriller',

    # Non-fiction - Art/Culture
    'art': 'Culture / Art',
    'music': 'Culture / Art',
    'culture': 'Culture / Art',
    'dance': 'Culture / Art',
    'painting': 'Culture / Art',

    # Non-fiction - Science/Technology
    'science': 'Scientific / Academic',
    'popular science': 'Popular Science',
    'nature': 'Non-fiction',
    'animals': 'Non-fiction',
    'technology': 'Non-fiction',
    'engineering': 'Scientific / Academic',
    'physics': 'Scientific / Academic',
    'chemistry': 'Scientific / Academic',
    'biology': 'Scientific / Academic',

    # Non-fiction - Self-Help/Business/Psychology
    'business': 'Business / Self-Help',
    'self-help': 'Business / Self-Help',
    'psychology': 'Business / Self-Help',
    'philosophy': 'Religion / Philosophy',
    'spirituality': 'Religion / Philosophy',
    'religion': 'Religion / Philosophy',

    # Non-fiction - Education/Reference/Guide
    'education': 'Manual / Education',
    'reference': 'Manual / Education',
    'guide': 'Guide / Hobby',
    'travel': 'Guide / Hobby',
    'travel guide': 'Guide / Hobby',
    'cookbook': 'Guide / Hobby',
    'recipe': 'Guide / Hobby',
    'food': 'Guide / Hobby',
    'cooking': 'Guide / Hobby',
    'gardening': 'Guide / Hobby',
    'hobby': 'Guide / Hobby',
    'craft': 'Guide / Hobby',
    'crafts': 'Guide / Hobby',
    'health': 'Non-fiction',
    'medical': 'Non-fiction',
    'sports': 'Non-fiction',
    'parenting': 'Guide / Hobby',
    'languages': 'Manual / Education',
    'legal': 'Non-fiction',
    'political': 'Non-fiction',
    'sociology': 'Non-fiction',
    'social science': 'Non-fiction',
    'history': 'Non-fiction',
}


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

        # Cap the requested limit so we don't return more than the API allows locally
        limit = min(limit, 20)

        logger.info(f"Open Library: Searching by title: '{query}'")

        try:
            params = {
                "title": query,
                "limit": limit,
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

            # Extract subjects (genres) from Open Library
            subjects = []
            for subject in book_data.get("subjects", []):
                if isinstance(subject, dict):
                    subjects.append(subject.get("name", "").lower().strip())
                else:
                    subjects.append(str(subject).lower().strip())

            # Extract description (can be str or dict)
            description = None
            desc_data = book_data.get("description")
            if isinstance(desc_data, dict):
                description = desc_data.get("value", "").strip()
            elif isinstance(desc_data, str):
                description = desc_data.strip()

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
                "subjects": subjects,  # Raw subjects from OL
                "description": description,
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

    @staticmethod
    def map_ol_subjects_to_genres(ol_subjects: List[str]) -> List[str]:
        """
        Map Open Library subjects to application genres.

        Args:
            ol_subjects: List of subjects from Open Library (already lowercased)
                        Subjects may contain multiple genres separated by commas.

        Returns:
            List of matching application genre names
        """
        mapped_genres: Set[str] = set()

        for subject in ol_subjects:
            # Clean subject and split by comma since OL often groups genres like "fiction, romance, historical"
            subject = subject.lower().strip()

            # Split by comma to handle compound subjects
            individual_subjects = [s.strip() for s in subject.split(',')]

            for individual_subject in individual_subjects:
                if not individual_subject:
                    continue

                # Try exact match first
                if individual_subject in OL_SUBJECT_TO_GENRE_MAPPING:
                    mapped_genres.add(OL_SUBJECT_TO_GENRE_MAPPING[individual_subject])
                else:
                    # Try partial matches
                    for ol_pattern, genre in OL_SUBJECT_TO_GENRE_MAPPING.items():
                        if ol_pattern in individual_subject or individual_subject in ol_pattern:
                            mapped_genres.add(genre)
                            break

        # Return sorted list to ensure consistency
        return sorted(list(mapped_genres))

    @staticmethod
    def get_genre_ids_for_subjects(
        ol_subjects: List[str]
    ) -> List[int]:
        """
        Get genre IDs from database matching Open Library subjects.

        Requires database context to be active.

        Args:
            ol_subjects: List of subjects from Open Library

        Returns:
            List of genre IDs that match the subjects
        """
        from app.models import Genre
        from flask_babel import gettext as _real

        mapped_genre_names = OpenLibraryClient.map_ol_subjects_to_genres(ol_subjects)

        if not mapped_genre_names:
            logger.info(f"No genres mapped from OL subjects: {ol_subjects}")
            return []

        genre_ids = []
        for genre_name in mapped_genre_names:
            # Query for genre - need to check both with and without translation
            genre = Genre.query.filter(
                Genre.name.ilike(genre_name)
            ).first()

            if genre:
                genre_ids.append(genre.id)
                logger.info(f"Mapped OL subject to genre ID {genre.id}: {genre_name}")
            else:
                logger.warning(f"No genre found for: {genre_name}")

        return genre_ids
