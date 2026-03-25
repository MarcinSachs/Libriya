import math
import re
from collections import Counter
from typing import Dict, List

from app import db
from app.models import Book


class RecommendationService:
    # Very small stopword list for Polish and English. Extend as needed.
    STOPWORDS = {
        'the', 'and', 'for', 'with', 'that', 'this', 'from', 'your', 'you', 'are', 'was', 'were',
        'jest', 'to', 'na', 'do', 'z', 'oraz', 'ale', 'się', 'nie', 'tak', 'jak', 'co', 'może',
        'czy', 'a', 'o', 'w', 'po', 'przez'
    }

    @staticmethod
    def _normalize_text(value: str) -> str:
        if not value:
            return ''
        text = value.lower()
        text = re.sub(r"[^a-ząćęłńóśżź0-9\s]", ' ', text)
        return re.sub(r'\s+', ' ', text).strip()

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        text = RecommendationService._normalize_text(text)
        tokens = [token for token in text.split(' ') if token and len(
            token) > 2 and token not in RecommendationService.STOPWORDS]
        return tokens

    @staticmethod
    def _tf(tokens: List[str]) -> Dict[str, float]:
        if not tokens:
            return {}
        cnt = Counter(tokens)
        total = sum(cnt.values())
        return {token: freq / total for token, freq in cnt.items()}

    @staticmethod
    def _cosine_similarity(a: Dict[str, float], b: Dict[str, float]) -> float:
        if not a or not b:
            return 0.0

        intersect = set(a.keys()) & set(b.keys())
        dot = sum(a[token] * b[token] for token in intersect)
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))

        if not norm_a or not norm_b:
            return 0.0

        return dot / (norm_a * norm_b)

    @staticmethod
    def _build_document_vector(book: Book) -> Dict[str, float]:
        words = []

        # Use title + description + authors + genres.
        words.extend(RecommendationService._tokenize(book.title or ''))
        words.extend(RecommendationService._tokenize(book.description or ''))
        words.extend(RecommendationService._tokenize(' '.join([a.name for a in book.authors or []])))
        words.extend(RecommendationService._tokenize(' '.join([g.name for g in book.genres or []])))

        return RecommendationService._tf(words)

    @staticmethod
    def get_recommendations_for_user(user, max_results: int = 8, candidate_limit: int = 300):
        if not user or not user.favorites:
            return []

        favorite_books = user.favorites
        favorite_author_ids = {author.id for book in favorite_books for author in book.authors}
        favorite_genre_ids = {genre.id for book in favorite_books for genre in book.genres}

        # Build aggregated user profile vector from favorites
        profile_tokens = []
        for book in favorite_books:
            profile_tokens.extend(RecommendationService._tokenize(book.title or ''))
            profile_tokens.extend(RecommendationService._tokenize(book.description or ''))
            profile_tokens.extend(RecommendationService._tokenize(' '.join([a.name for a in book.authors or []])))
            profile_tokens.extend(RecommendationService._tokenize(' '.join([g.name for g in book.genres or []])))

        if not profile_tokens:
            return []

        user_profile_vector = RecommendationService._tf(profile_tokens)

        # Choose candidates within user's access scope
        query = Book.query
        if user.is_super_admin:
            pass
        elif user.role == 'admin':
            query = query.filter(Book.tenant_id == user.tenant_id)
        else:
            user_library_ids = [lib.id for lib in user.libraries]
            if not user_library_ids:
                return []
            query = query.filter(Book.library_id.in_(user_library_ids))

        favorite_ids = {book.id for book in favorite_books}
        query = query.filter(~Book.id.in_(favorite_ids))

        candidates = query.options(
            db.subqueryload(Book.authors),
            db.subqueryload(Book.genres)
        ).limit(candidate_limit).all()

        scored = []
        for candidate in candidates:
            cand_author_ids = {a.id for a in candidate.authors}
            cand_genre_ids = {g.id for g in candidate.genres}

            author_matches = len(cand_author_ids & favorite_author_ids)
            genre_matches = len(cand_genre_ids & favorite_genre_ids)

            candidate_vector = RecommendationService._build_document_vector(candidate)
            text_similarity = RecommendationService._cosine_similarity(user_profile_vector, candidate_vector)

            # Score weights:
            # - author match strong
            # - genre match medium
            # - description/title similarity strong
            score = 0.0
            score += author_matches * 6
            score += genre_matches * 3
            score += text_similarity * 30

            if score <= 0:
                continue

            scored.append((score, candidate))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [book for _, book in scored[:max_results]]
