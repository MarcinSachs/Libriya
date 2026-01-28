# PWA + Enhanced Book Search - Implementation Guide

## 🎯 Co zostało zaimplementowane?

### 1. **Wyszukiwanie Książek** 📚

Trzy metody dodawania książek do biblioteki:

#### a) **Skanowanie ISBN/Barcode'u** (Mobilne)
- Dostępne tylko na urządzeniach mobilnych
- Przycisk `Scan ISBN/Barcode` pojawia się na mobilnych
- Używa kamery do odczytania kodu QR lub kodu kreskowego
- **Biblioteka:** `html5-qrcode`
- Po zeskanowaniu automatycznie wyszukuje dane z Open Library

#### b) **Wyszukiwanie po ISBN**
- Wpisz numer ISBN ręcznie lub odczytany ze skanera
- Klawisz `Search` pobiera dane z Open Library API
- Wypełnia: tytuł, autor, rok wydania, okładka

#### c) **Wyszukiwanie po Tytule** (NEW!)
- Wpisz przynajmniej 3 znaki tytułu
- System zwraca listę książek z miniaturkami okładek
- Możliwość wyboru książki z listy
- Dane są automatycznie wypełniane w formularzu

---

### 2. **Progressive Web App (PWA)** 📱

Aplikacja działa teraz jak aplikacja mobilna:

#### Cechy:
- ✅ **Instalacja na home screen** (iOS, Android, Desktop)
- ✅ **Offline support** - cached pages dostępne bez internetu
- ✅ **API caching** - ostatnie wyszukiwania są cache'owane
- ✅ **Szybsze ładowanie** - Service Worker cache
- ✅ **App-like UI** - fullscreen, standalone display
- ✅ **Icona aplikacji** - niestandardowy icon na home screen

#### Jak zainstalować?

**Android (Chrome):**
1. Otwórz aplikację w Chrome
2. Menu (3 kropki) → "Install app"
3. Potwierdź

**iOS (Safari):**
1. Otwórz aplikację w Safari
2. Udostępnij (Share) → "Add to Home Screen"
3. Potwierdź

**Desktop (PWA):**
1. Otwórz w Chrome
2. Adres URL → Ikona "Zainstaluj"
3. Potwierdź

---

## 🗄️ Zmiany w Bazie Danych

### Model `Book`
```python
# BEFORE
isbn = db.Column(db.String(13), unique=True, nullable=False, index=True)

# AFTER
isbn = db.Column(db.String(13), unique=True, nullable=True, index=True)
```

**Migracja:** Uruchom `flask db upgrade` aby zaktualizować bazę.

---

## 🔌 Nowe API Endpointy

### 1. **Wyszukiwanie po Tytule**
```
GET /api/v1/search/title?q=<query>&limit=10
```

**Parametry:**
- `q` (required) - co najmniej 3 znaki
- `limit` (optional) - max 20, default 10

**Odpowiedź:**
```json
{
  "results": [
    {
      "title": "The Hobbit",
      "authors": ["J.R.R. Tolkien"],
      "isbn": "9780545003957",
      "year": 1937,
      "cover_id": 4823208
    }
  ],
  "total": 1
}
```

### 2. **Wyszukiwanie po ISBN** (Istniejący)
```
GET /api/v1/isbn/<isbn>
```

---

## 📁 Nowe Pliki

```
app/
├── static/
│   ├── manifest.json              # PWA konfiguracja
│   └── service-worker.js          # Offline cache logic
│
└── templates/
    └── book_add.html              # Zaktualizowany (skanowanie + wyszukiwanie po tytule)

migrations/
└── versions/
    └── make_isbn_nullable.py      # Migracja bazy danych
```

---

## 🚀 Jak Uruchomić

### Instalacja

1. **Update dependencies** (jeśli jest requirements.txt):
```bash
pip install flask requests  # Już powinny być zainstalowane
```

2. **Uruchom migrację** (jeśli używasz Alembic):
```bash
flask db upgrade
```

3. **Restart aplikacji**:
```bash
python libriya.py
```

---

## 🧪 Testowanie Funkcjonalności

### Test 1: Wyszukiwanie po ISBN
1. Idź do `Add Book`
2. Wpisz ISBN: `9780545003957` (The Hobbit)
3. Kliknij `Search`
4. Dane powinny się załadować

### Test 2: Wyszukiwanie po Tytule
1. Idź do `Add Book`
2. W sekcji "Search by Title" wpisz: `Harry Potter`
3. Kliknij `Search` (lub Enter)
4. Kliknij na jedną z wyników
5. Dane powinny się załadować

### Test 3: Skanowanie (Mobilne)
1. Otwórz aplikację na telefonie
2. Idź do `Add Book`
3. Kliknij `Scan ISBN/Barcode`
4. Zeskanuj kod kreskowy z książki
5. Dane powinny się załadować automatycznie

### Test 4: PWA (Instalacja)
1. Otwórz aplikację na telefonie lub na Chrome
2. Menu → Install app (lub Share → Add to Home Screen na iOS)
3. Otwórz zainstalowaną aplikację
4. Powinna pracować jak zwykła aplikacja
5. Spróbuj wyłączyć internet i wróć do strony głównej - powinna być dostępna

---

## 🔒 Bezpieczeństwo

### Walidacja ISBN
- Min. 10 znaków, Max. 13 znaków
- Tylko cyfry (hyphens są usuwane)

### API Security
- Open Library API jest publiczne (bez auth)
- Timeout: 10 sekund
- Max timeout na tę API: 20 wyników

### Service Worker Cache
- Tylko GET requesty są cache'owane
- POST/PUT/DELETE są zawsze fresh
- Stary cache jest czyszczony przy aktualizacji

---

## 📝 Konfiguracja Offline

Service Worker cache'uje:
- ✅ Statyczne strony HTML
- ✅ CSS, JavaScript, obrazy
- ✅ Ostatnie API responses
- ✅ Bootstrap i biblioteki z CDN

**Offline behavior:**
- Jeśli strona jest w cache → pokaż cached version
- Jeśli API jest offline → pokaż cached response lub error

---

## 🐛 Troubleshooting

### Service Worker się nie rejestruje
- Sprawdź czy aplikacja jest na HTTPS lub localhost
- Otwórz DevTools → Application → Service Workers
- Sprawdź logs w konsoli

### Skanowanie nie działa
- Sprawdzenie czy browser ma dostęp do kamery
- Chrome, Firefox, Safari (iOS 14+) wspierają WebRTC

### Aplikacja nie się installuje
- PWA wymaga min. icon'u 192x192px (masz)
- HTTPS lub localhost
- Valid manifest.json

---

## 📚 Przydatne Linki

- [Open Library API](https://openlibrary.org/developers/api)
- [MDN - Service Workers](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)
- [MDN - Web App Manifest](https://developer.mozilla.org/en-US/docs/Web/Manifest)
- [html5-qrcode](https://github.com/mebjas/html5-qrcode)

---

## 🚀 Następne Kroki (Opcjonalnie)

1. **Push Notifications** - Powiadomienia o nowych książkach
2. **Background Sync** - Sync'owanie danych offline'owo
3. **Offline Mode Indicators** - UI pokazujący czy app jest online/offline
4. **Import/Export** - Backup biblioteki
5. **Native App** - React Native/Flutter jeśli będzie taka potrzeba

---

**Wdrożone przez:** GitHub Copilot
**Data:** 27-01-2026
