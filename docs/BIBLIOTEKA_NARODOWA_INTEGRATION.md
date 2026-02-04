# Biblioteka Narodowa (Polish National Library) Integration

## Overview

The **Biblioteka Narodowa** module is a premium feature that provides enriched book metadata from Poland's National Library API. When enabled, it becomes the primary source for book information, with Open Library as a fallback.

**API Documentation**: https://data.bn.org.pl/docs/bibs

---

## Features

### Metadata Sources

- **ISBN/ISSN lookup**: Search for books using ISBN-13 or ISBN-10
- **Enriched metadata**: Titles, authors, publication years, publishers
- **Polish classification**: Maps Polish book types to application genres
- **Fallback support**: Automatically falls back to Open Library if book not found

### Cover Images

⚠️ **Important**: Biblioteka Narodowa does NOT provide cover images. Covers always come from:

1. **Premium Bookcover API** (if enabled) - Goodreads covers via bookcover.longitood.com
2. **Open Library** (fallback) - Free covers from Open Library
3. **Local default** (if no covers found anywhere)

---

## Installation & Setup

### 1. Enable the Module

Add to your `.env` file:

```bash
# Enable Biblioteka Narodowa metadata
PREMIUM_BIBLIOTEKA_NARODOWA_ENABLED=true

# Optional: Enable premium bookcover for better covers
PREMIUM_BOOKCOVER_ENABLED=true
```

### 2. No Additional Configuration Needed

The module uses the public BN API endpoint - no API keys or credentials required!

```python
# In app/__init__.py - initialization is automatic
from app.services.premium.manager import PremiumManager

def create_app(config_class=Config):
    # ... app setup ...
    PremiumManager.init()  # Registers all premium modules including BN
    # ... rest of setup ...
```

---

## Usage

### Automatic Integration

The module is automatically integrated into the book search flow:

```python
from app.services.book_service import BookSearchService

# Search by ISBN - will automatically try BN first, then fallback to OL
book = BookSearchService.search_by_isbn("9788375799538")

# book will contain:
# {
#     'isbn': '9788375799538',
#     'title': 'Wiedzmin: Ostatnie zyczenie',
#     'authors': ['Sapkowski, Andrzej'],
#     'year': 2022,
#     'publisher': 'Wydawnictwo Supernowa',
#     'genres': ['Fiction', 'Fantasy'],  # Mapped from BN categories
#     'source': 'biblioteka_narodowa',
#     'bn_id': '123456789',
#     'cover': {
#         'url': 'https://openlibrary.org/...',
#         'source': 'open_library'  # or 'premium_bookcover'
#     }
# }
```

### Direct API Access

You can also call the service directly:

```python
from app.services.premium.manager import PremiumManager

if PremiumManager.is_enabled('biblioteka_narodowa'):
    result = PremiumManager.call(
        'biblioteka_narodowa',
        'search_by_isbn',
        isbn='9788375799538'
    )
    
    if result:
        print(f"Found: {result['title']} by {result['authors']}")
    else:
        print("Not found in BN - fallback to Open Library")
```

---

## Architecture

### Service Structure

```
app/services/premium/metadata/
├── __init__.py
└── biblioteka_narodowa_service.py
    └── BibliotekaNarodowaService
        ├── search_by_isbn(isbn)
        ├── _parse_bib_record(record, isbn)
        ├── _extract_authors(record)
        ├── _extract_year(record)
        ├── _extract_publisher(record)
        └── _extract_genres(record)
```

### Priority Flow

```
BookSearchService.search_by_isbn()
│
├─ BN enabled? ─ YES ─► BibliotekaNarodowaService.search_by_isbn()
│                      ├─ Found? ─ YES ─► Return + enhance cover
│                      └─ Found? ─ NO ──┐
└─ NO ────────────────────────────────┤
                                      └─► OpenLibraryClient.search_by_isbn()
                                          ├─ Found? ─ YES ─► Return + enhance cover
                                          └─ Found? ─ NO ──► Try premium covers only
```

### Cover Priority

Regardless of where metadata comes from:

```
CoverService.get_cover_url()
│
├─► Try Premium Bookcover API (if enabled + licensed)
│   └─ Found? ─ YES ─► Return premium cover
│
├─► Try cover from source metadata (OL/BN metadata)
│   └─ Found? ─ YES ─► Return source cover
│
├─► Try Open Library ISBN lookup
│   └─ Found? ─ YES ─► Return OL cover
│
└─► Use local default image
```

---

## Genre Mapping

The service maps Polish book types from BN to application genres:

### Fiction
- `beletrystyka` → Fiction
- `powieść` → Fiction
- `fantastyka` → Fantasy
- `romans` → Romance / Contemporary
- `kryminał` → Crime / Thriller

### Non-Fiction
- `publikacja naukowa` → Scientific / Academic
- `poradnik` → Business / Self-Help
- `podręcznik` → Manual / Education

### Special Categories
- `literatura dziecięca` → Children
- `literatura młodzieżowa` → Young Adult
- `dramat` → Poetry / Drama

See [`biblioteka_narodowa_service.py`](../app/services/premium/metadata/biblioteka_narodowa_service.py) for complete mapping.

---

## API Details

### Request Format

```bash
curl "https://data.bn.org.pl/api/institutions/bibs.json?isbnIssn=9788375799538"
```

### Response Format

```json
[
  {
    "id": "123456789",
    "title": "Wiedzmin: Ostatnie zyczenie",
    "creator": ["Sapkowski, Andrzej"],
    "date": "2022",
    "publisher": "Wydawnictwo Supernowa",
    "type": "beletrystyka",
    "subject": ["fantasy", "literature"]
  }
]
```

### Timeout

- Default timeout: 10 seconds
- No retry logic (falls back to OL on timeout)

---

## Troubleshooting

### Module Not Enabled

```python
if not PremiumManager.is_enabled('biblioteka_narodowa'):
    logger.warning("BN module is disabled - check PREMIUM_BIBLIOTEKA_NARODOWA_ENABLED")
```

### ISBN Not Found in BN

This is expected - not all books are in the Polish National Library database:

```python
# Book found in BN
if result and result['source'] == 'biblioteka_narodowa':
    print("Using BN data")

# Book not in BN, used Open Library
elif result and result['source'] == 'open_library':
    print("Book not in BN, using OL data")
```

### Poor Cover Quality

If you want better covers:

1. Enable premium bookcover service
2. Ensure you have a valid license for bookcover.longitood.com
3. Covers will automatically be upgraded when available

```bash
PREMIUM_BOOKCOVER_ENABLED=true
```

---

## Performance

- **API Response Time**: ~200-500ms
- **Cache**: No caching at service level (use application-level caching if needed)
- **Rate Limiting**: BN API has no public rate limits, but use responsibly
- **Timeout**: 10 seconds before fallback to Open Library

---

## Testing

### Manual Test

```bash
# Test with a Polish book ISBN
python -c "
from app.services.book_service import BookSearchService

book = BookSearchService.search_by_isbn('9788375799538')
if book:
    print(f'Title: {book[\"title\"]}')
    print(f'Source: {book[\"source\"]}')
    print(f'Authors: {book[\"authors\"]}')
    print(f'Genres: {book.get(\"genres\", [])}')
else:
    print('Not found')
"
```

### API Test

```bash
# Direct API test
curl "https://data.bn.org.pl/api/institutions/bibs.json?isbnIssn=9788375799538"
```

---

## Future Enhancements

- [ ] Title search support (if BN adds good title search API)
- [ ] Caching layer for repeated ISBN lookups
- [ ] Extended genre mapping
- [ ] Subject classification export
- [ ] Library holdings information
- [ ] ISBN correction/normalization

---

## References

- **BN API Docs**: https://data.bn.org.pl/docs/bibs
- **Service Code**: [biblioteka_narodowa_service.py](../app/services/premium/metadata/biblioteka_narodowa_service.py)
- **Integration Point**: [book_service.py](../app/services/book_service.py#L50-L70)
- **Premium System**: [PREMIUM_SYSTEM_SUMMARY.md](PREMIUM_SYSTEM_SUMMARY.md)
