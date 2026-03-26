import math
import re
from collections import Counter
from typing import Dict, List

from app import db
from app.models import Book

# Lazy singleton – ładowanie modelu Stempel (~3 s) odbywa się tylko raz.
_stempel_stemmer = None


def _get_stempel_stemmer():
    """Zwraca (i ew. inicjalizuje) singleton stemmera Stempel dla języka polskiego."""
    global _stempel_stemmer
    if _stempel_stemmer is None:
        try:
            from pystempel import Stemmer
            _stempel_stemmer = Stemmer.polimorf()
        except Exception:
            _stempel_stemmer = False  # False sygnalizuje brak biblioteki
    return _stempel_stemmer if _stempel_stemmer is not False else None


def _detect_language(text: str) -> str:
    """Wykrywa język tekstu. Zwraca 'pl', 'en' lub 'unknown'.

    Używa langdetect na połączonym tekście (tytuł + opis), więc działa
    poprawnie nawet gdy tytuł po polsku nie zawiera polskich znaków
    diakrytycznych (np. 'zagadki jezykowe').
    """
    if not text or len(text.strip()) < 10:
        return 'unknown'
    try:
        from langdetect import detect, LangDetectException
        return detect(text)
    except Exception:
        return 'unknown'


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
    def _stem_pl(token: str) -> str:
        """Stemuje polski token przez Stempel. Dla nieznanych słów zwraca token bez zmian."""
        stemmer = _get_stempel_stemmer()
        if stemmer is None:
            return token
        result = stemmer(token)
        return result if result is not None else token

    @staticmethod
    def _tokenize(text: str, lang: str = 'unknown') -> List[str]:
        """Tokenizuje tekst, stosując stemmer właściwy dla wykrytego języka.

        - lang='pl'  → Stempel (morfologika polska, działa też dla tekstów
                        bez polskich znaków diakrytycznych)
        - inne języki → brak stemowania (angielski i inne języki są
                        znacznie mniej fleksyjne, brak stemowania nie psuje wyników)
        """
        text = RecommendationService._normalize_text(text)
        raw_tokens = [
            token for token in text.split(' ')
            if token and len(token) > 2 and token not in RecommendationService.STOPWORDS
        ]
        if lang == 'pl':
            return [RecommendationService._stem_pl(t) for t in raw_tokens]
        return raw_tokens

    @staticmethod
    def _tf(tokens: List[str]) -> Dict[str, float]:
        if not tokens:
            return {}
        cnt = Counter(tokens)
        total = sum(cnt.values())
        return {token: freq / total for token, freq in cnt.items()}

    @staticmethod
    def _compute_idf(documents: List[List[str]]) -> Dict[str, float]:
        """Compute smoothed IDF for each token across a list of token lists.

        Formula: idf(t) = log((N + 1) / (df(t) + 1)) + 1
        where N = number of documents and df(t) = number of docs containing t.
        The smoothing prevents zero division and gives unseen terms a non-zero
        fallback weight of 1.0.
        """
        n = len(documents)
        df: Counter = Counter()
        for tokens in documents:
            for token in set(tokens):
                df[token] += 1
        return {token: math.log((n + 1) / (count + 1)) + 1.0
                for token, count in df.items()}

    @staticmethod
    def _tfidf(tokens: List[str], idf: Dict[str, float]) -> Dict[str, float]:
        """Return a TF-IDF vector for the given token list."""
        tf = RecommendationService._tf(tokens)
        return {token: tf_val * idf.get(token, 1.0) for token, tf_val in tf.items()}

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
    def _book_text_tokens(book: Book) -> List[str]:
        """Zwraca tokeny z tytułu i opisu książki (bez gatunków i autorów).

        Używane wyłącznie do budowania wektorów TF-IDF.
        Gatunki i autorzy są obsługiwane osobno przez genre_score i author_score,
        więc wykluczamy je z podobieństwa kosinusowego, żeby uniknąć podwójnego
        liczenia (double-counting) sygnałów strukturalnych.
        """
        combined_text = ' '.join(filter(None, [book.title, book.description]))
        lang = _detect_language(combined_text)
        tokens: List[str] = []
        tokens.extend(RecommendationService._tokenize(book.title or '', lang=lang))
        tokens.extend(RecommendationService._tokenize(book.description or '', lang=lang))
        return tokens

    @staticmethod
    def _book_tokens(book: Book) -> List[str]:
        """Zwraca wszystkie tokeny książki (treść + gatunki + autorzy).

        Używane do obliczania IDF na korpusie kandydatów, żeby rzadkie terminy
        (np. nazwy własne, specjalistyczne słownictwo) otrzymały wyższe wagi.
        """
        tokens = RecommendationService._book_text_tokens(book)
        author_tokens = RecommendationService._tokenize(
            ' '.join([a.name for a in book.authors or []]), lang='pl')
        genre_tokens = RecommendationService._tokenize(
            ' '.join([g.name for g in book.genres or []]), lang='pl')
        tokens.extend(author_tokens)
        tokens.extend(genre_tokens)
        return tokens

    @staticmethod
    def _build_document_vector(book: Book) -> Dict[str, float]:
        """Build a simple TF vector (kept for backward compatibility)."""
        return RecommendationService._tf(RecommendationService._book_tokens(book))

    @staticmethod
    def _coverage(candidate_ids: set, reference_ids: set) -> float:
        """Fraction of *candidate* attributes that appear in the reference set.

        Returns a value in [0, 1].  Normalising by the candidate's own count
        means a book whose single author is a known favourite scores 1.0,
        regardless of how many other favourite authors the user has.
        """
        if not candidate_ids:
            return 0.0
        return len(candidate_ids & reference_ids) / len(candidate_ids)

    @staticmethod
    def get_recommendations_for_user(user, max_results: int = 8, candidate_limit: int = 300):
        if not user or not user.favorites:
            return []

        favorite_books = user.favorites
        favorite_author_ids = {author.id for book in favorite_books for author in book.authors}
        favorite_genre_ids = {genre.id for book in favorite_books for genre in book.genres}

        # ------------------------------------------------------------------
        # 1. Build candidate set, prioritising genre/author overlap
        # ------------------------------------------------------------------
        # Base query scoped to what the user can access.
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

        load_opts = [db.subqueryload(Book.authors), db.subqueryload(Book.genres)]

        from app.models import book_genres as bg_table, book_authors as ba_table

        seen_ids: set = set()
        candidates: List[Book] = []

        # Pull books that share at least one genre with the user's favourites.
        if favorite_genre_ids:
            genre_q = (
                query.join(bg_table, Book.id == bg_table.c.book_id)
                .filter(bg_table.c.genre_id.in_(favorite_genre_ids))
                .distinct()
                .options(*load_opts)
                .limit(candidate_limit)
            )
            for book in genre_q.all():
                if book.id not in seen_ids:
                    seen_ids.add(book.id)
                    candidates.append(book)

        # Pull books that share at least one author with the user's favourites.
        if favorite_author_ids:
            author_q = (
                query.join(ba_table, Book.id == ba_table.c.book_id)
                .filter(ba_table.c.author_id.in_(favorite_author_ids))
                .distinct()
                .options(*load_opts)
                .limit(candidate_limit)
            )
            for book in author_q.all():
                if book.id not in seen_ids:
                    seen_ids.add(book.id)
                    candidates.append(book)

        # Fill remaining slots so we always return something even when the
        # user's favourite genres/authors are absent from the library.
        remaining = candidate_limit - len(candidates)
        if remaining > 0:
            filler_q = (
                query.filter(~Book.id.in_(seen_ids))
                .options(*load_opts)
                .limit(remaining)
            )
            candidates.extend(filler_q.all())

        if not candidates:
            return []

        # ------------------------------------------------------------------
        # 2. Build TF-IDF representations
        # ------------------------------------------------------------------
        # IDF liczymy na pełnym korpusie (treść + gatunki + autorzy), żeby
        # rzadkie terminy tematyczne miały wyższe wagi niż powszechne słowa.
        idf_corpus: List[List[str]] = [
            RecommendationService._book_tokens(b) for b in candidates
        ]
        idf = RecommendationService._compute_idf(idf_corpus)

        # Wektory TF-IDF profilu i kandydatów budujemy TYLKO z tytułu i opisu.
        # Gatunki i autorzy są osobnymi sygnałami (genre_score, author_score),
        # więc nie mieszamy ich z podobieństwem treściowym.
        candidate_tokens: List[List[str]] = [
            RecommendationService._book_text_tokens(b) for b in candidates
        ]

        profile_tokens: List[str] = []
        for book in favorite_books:
            profile_tokens.extend(RecommendationService._book_text_tokens(book))

        if not profile_tokens:
            return []

        user_profile_vector = RecommendationService._tfidf(profile_tokens, idf)

        # ------------------------------------------------------------------
        # 3. Score and rank candidates
        # ------------------------------------------------------------------
        scored = []
        for i, candidate in enumerate(candidates):
            cand_author_ids = {a.id for a in candidate.authors}
            cand_genre_ids = {g.id for g in candidate.genres}

            # Coverage: what fraction of the candidate's own authors/genres
            # are already represented in the user's favourite set?
            author_score = RecommendationService._coverage(cand_author_ids, favorite_author_ids)
            genre_score = RecommendationService._coverage(cand_genre_ids, favorite_genre_ids)

            candidate_vector = RecommendationService._tfidf(candidate_tokens[i], idf)
            text_similarity = RecommendationService._cosine_similarity(
                user_profile_vector, candidate_vector
            )

            # Composite score weights:
            #   text_similarity (TF-IDF cosine)  — 50 pts  richest signal
            #   author coverage                  — 30 pts  strong structural proxy
            #   genre coverage                   — 20 pts  broad thematic signal
            #
            if text_similarity == 0:
                continue

            score = text_similarity * 50 + author_score * 30 + genre_score * 20

            if score <= 0:
                continue

            scored.append((score, candidate))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [book for _, book in scored[:max_results]]
