# Rozbudowa Wyszukiwania Książek - Dokumentacja Implementacji

## 📋 Przegląd

Zaimplementowana pełna integracja z trzema źródłami danych do wyszukiwania książek:

1. **Biblioteka Narodowa (BN)** - Polska Biblioteka Narodowa z dwoma katalogami
2. **Open Library API** - Fallback dla książek nie znalezionych w BN
3. **Bookcover API** - Pobieranie okładek z Goodreads via bookcover.longitood.com
4. **Domyślny obraz** - Fallback gdy okładka nie jest dostępna

---

## 🏗️ Struktura Nowych Modułów

### `app/services/` - Nowa warstwa serwisów

```
app/services/
├── __init__.py                      # Exports głównych klas
├── isbn_validator.py                # Walidacja i normalizacja ISBN
├── bn_api.py                        # Integracja z BN API
├── openlibrary_service.py          # Refactored Open Library API
├── cover_service.py                 # Zarządzanie pobieraniem okładek
└── book_service.py                  # Orchestrator - główna logika
```

---

## 🔍 Hierarchia Wyszukiwania

### 1. Wyszukiwanie po ISBN

```
ISBN Input
    ↓
[ISBNValidator] - normalizacja & walidacja
    ↓
[BookSearchService.search_by_isbn()]
    ├─→ [BNAPIClient.search_by_isbn()]
    │   ├─→ Połączone katalogi BN (/api/networks/bibs.json)
    │   └─→ Bezpośrednia BN (/api/institutions/bibs.json) [fallback]
    │
    ├─→ [OpenLibraryClient.search_by_isbn()] [jeśli brak w BN]
    │
    └─→ [CoverService.get_cover_url()]
        ├─→ Z source (OL cover)
        ├─→ Bookcover API (Goodreads)
        └─→ Local default
    ↓
Unified Response
{
    "title": "...",
    "authors": [...],
    "isbn": "...",
    "source": "bn_networks|bn_direct|open_library",
    "cover": {"url": "...", "source": "open_library|bookcover_api|local_default"}
}
```

### 2. Wyszukiwanie po Tytule

```
Title Query
    ↓
[BookSearchService.search_by_title()]
    ├─→ [BNAPIClient.search_by_title()]
    │   └─→ Połączone katalogi BN
    │
    ├─→ [OpenLibraryClient.search_by_title()] [fill gaps]
    │
    ├─→ Deduplikacja po ISBN
    │
    └─→ [CoverService] dla każdego wyniku
    ↓
List of Unified Results
```

---

## 📦 API Endpoints (Refaktoryzowane)

### `GET /api/v1/isbn/<isbn>`

**Parametry query:**
- `include_bn` (bool, default: true) - Wyszukiwać w BN

**Response:**
```json
{
    "title": "The Hobbit",
    "author": "J.R.R. Tolkien",
    "year": 1937,
    "isbn": "978-0-545-00395-7",
    "publisher": "Allen & Unwin",
    "source": "bn_networks",
    "cover_image": "https://covers.openlibrary.org/b/id/4823208-L.jpg",
    "cover_source": "open_library"
}
```

### `GET /api/v1/search/title`

**Parametry query:**
- `q` (string, required) - Fraza wyszukiwania (min 3 znaki)
- `limit` (int, default: 10, max: 20)
- `author` (string, optional) - Filtr po autorze
- `include_bn` (bool, default: true) - Wyszukiwać w BN

**Response:**
```json
{
    "results": [
        {
            "title": "...",
            "authors": [...],
            "isbn": "...",
            "year": 1937,
            "source": "bn_networks",
            "cover_id": "https://covers.openlibrary.org/b/id/4823208-S.jpg",
            "cover_source": "open_library"
        }
    ],
    "total": 10
}
```

---

## 🔐 Bezpieczeństwo

### Walidacja ISBN
- Akceptuje ISBN-10 i ISBN-13
- Sprawdza sumy kontrolne
- Normalizuje (usuwa hyphens, spacje)
- Format: `ISBNValidator.is_valid(isbn)` → True/False

### Bezpieczeństwo URL (SSRF Prevention)
- Waliduje schemat (tylko HTTP/HTTPS)
- Blokuje localhost i private IP
- Limit rozmiaru pobieranego pliku: 5MB
- Timeout: 5-15 sekund zależnie od API

### Timeout
- BN API: 15 sekund
- Open Library: 10 sekund
- Bookcover API: 5 sekund

---

## 📝 Implementacja Szczegółów

### 1. `app/services/isbn_validator.py`

```python
# Walidacja
is_valid = ISBNValidator.is_valid("978-0-545-00395-7")  # True

# Normalizacja
normalized = ISBNValidator.normalize("978-0-545-00395-7")  # "9780545003957"

# Formatowanie
formatted = ISBNValidator.format_isbn_13("0545003954")  # "978-0-545-00395-4"

# Helper
is_valid, formatted_isbn = validate_isbn("978-0-545-00395-7")
```

### 2. `app/services/bn_api.py`

```python
from app.services.bn_api import BNAPIClient

# Wyszukiwanie po ISBN
book = BNAPIClient.search_by_isbn("9780545003957")

# Wyszukiwanie po tytule
books = BNAPIClient.search_by_title(
    title="The Hobbit",
    author="Tolkien",
    limit=10,
    use_networks=True
)
```

**Katalogi BN:**
- `networks` (default) - Połączone katalogi (bardziej kompletne)
- `direct` - Bezpośrednia BN (fallback)

### 3. `app/services/openlibrary_service.py`

```python
from app.services.openlibrary_service import OpenLibraryClient

# Wyszukiwanie po ISBN
book = OpenLibraryClient.search_by_isbn("9780545003957")

# Wyszukiwanie po tytule
books = OpenLibraryClient.search_by_title("The Hobbit", limit=10)

# URL okładki
url = OpenLibraryClient.get_cover_url(cover_id=4823208, size="L")
```

### 4. `app/services/cover_service.py`

```python
from app.services.cover_service import CoverService

# Pobierz URL okładki (hierarchia)
url, source = CoverService.get_cover_url(
    isbn="9780545003957",
    title="The Hobbit",
    author="J.R.R. Tolkien",
    cover_from_source="https://..."  # Z OL
)
# Returns: ("https://...", "open_library|bookcover_api|local_default")

# Pobierz i zapisz okładkę
filename = CoverService.download_and_save_cover(
    cover_url="https://...",
    upload_folder="/app/static/uploads"
)
```

**Hierarchia pokrywania:**
1. Open Library (jeśli źródło to OL)
2. Bookcover API (Goodreads)
3. Domyślny lokalny obraz

### 5. `app/services/book_service.py` - Orchestrator

```python
from app.services.book_service import BookSearchService

# Wyszukiwanie po ISBN
book = BookSearchService.search_by_isbn(
    isbn="9780545003957",
    use_bn=True,           # Spróbuj BN
    use_openlibrary=True   # Fallback OL
)
# Returns: dict z ujednoliconymi danymi

# Wyszukiwanie po tytule
books = BookSearchService.search_by_title(
    title="The Hobbit",
    author=None,
    limit=10,
    use_bn=True,
    use_openlibrary=True
)
# Returns: list[dict] ujednoliconych wyników

# Odpowiedź zawiera:
{
    "source": "bn_networks",
    "title": "...",
    "authors": [...],
    "isbn": "...",
    "year": 1937,
    "publisher": "...",
    "cover": {
        "url": "https://...",
        "source": "open_library|bookcover_api|local_default"
    }
}
```

---

## 🎨 Frontend (book_add.html)

### Zmiany w szablonie

1. **Przycisk skanowania** - jak wcześniej
2. **Wyszukiwanie po ISBN**
   - Teraz z BN jako pierwsze źródło
   - Pokazuje źródło danych i źródło okładki
   - Fallback do domyślnego obrazu

3. **Wyszukiwanie po tytule**
   - Integruje wyniki z BN i OL
   - Deduplikacja po ISBN
   - Ikony źródeł (🇵🇱 BN vs 📚 OL)

4. **Obsługa okładek**
   - Wspiera HTTP URLs z Bookcover API
   - Fallback do Open Library
   - `onerror` handler dla domyślnego obrazu

### Nowa logika JS

```javascript
// ISBN search teraz wysyła:
fetch(`/api/v1/isbn/${isbn}?include_bn=true`)

// Wyświetla źródło danych:
"Data from: Polish National Library | Cover: Open Library"

// Obsługuje brak okładki:
<img src="${coverUrl}" onerror="this.src='/static/images/default-book-cover.png'">
```

---

## 🧪 Testowanie

### Test 1: ISBN z BN
```
ISBN: 9788365646156 (Venus in furs - polska edycja)
Oczekiwane: Zwróci z BN Networks z danymi
```

### Test 2: ISBN z Open Library (fallback)
```
ISBN: 9780545003957 (The Hobbit)
Oczekiwane: BN brak → OL + okładka z OL
```

### Test 3: Wyszukiwanie po tytule
```
Query: "Harry Potter"
Oczekiwane: Mix wyników z BN i OL, bez duplikatów
```

### Test 4: Brak okładki
```
ISBN które ma metadane ale brak okładki
Oczekiwane: Pokazanie domyślnego SVG obrazu
```

---

## 📊 Logi

Wszystkie serwisy logują do `current_app.logger`:

```python
logger.info(f"BN: Searching by ISBN: {isbn}")
logger.debug(f"CoverService: Enhanced cover for '{title}': {cover_source}")
logger.error(f"BN API error for ISBN {isbn}: {e}")
```

Można monitorować w:
- Terminal (dev mode)
- `logs/` folder (jeśli skonfigurowany)

---

## 🚀 Wdrażanie

### 1. Wymogi
```bash
pip install requests  # Już zainstalowany
```

### 2. Aktualizacja katalogów tłumaczeń (opcjonalne)
```bash
python compile_translations.py
```

### 3. Testowanie
```bash
python libriya.py
# Przejdź do /books/add/ i testuj wyszukiwanie
```

---

## 🔄 Workflow Produkcyjny

1. ✅ Integracja BN API z fallback na OL
2. ✅ Pobieranie okładek z hierarchią
3. ✅ Walidacja ISBN
4. ✅ Bezpieczeństwo (SSRF, timeouts)
5. ✅ Frontend UI
6. ✅ Tłumaczenia
7. ⏳ Monitorowanie/Logging
8. ⏳ Caching (Redis - opcjonalne w przyszłości)

---

## 📚 Referencje API

- **BN API:** https://data.bn.org.pl/docs/bibs
- **Open Library:** https://openlibrary.org/dev/docs/api/books
- **Bookcover API:** https://github.com/w3slley/bookcover-api

---

## 💡 Przyszłe Ulepszenia

1. **Redis Cache** - Cache'owanie wyników BN i OL
2. **Asynchronous** - Celery dla pobierania okładek
3. **Better Error Messages** - Bardziej szczegółowe błędy
4. **Rate Limiting** - Ochrona przed spam'em
5. **Search History** - Zapamiętywanie ostatnich wyszukiwań
6. **Analytics** - Statystyki źródeł danych

