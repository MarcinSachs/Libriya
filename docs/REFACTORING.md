# Struktura projektuu Libriya

## Przegląd zmian

Ta dokumentacja opisuje reorganizację struktury projektu Libriya, mającej na celu poprawę utrzymanialności i skalowalnośćci.

## Nowa Struktura Folderów

### app/routes/
Podzielone pliki routów dla lepszej organizacji:
- **__init__.py** - Rejestracja wszystkich blueprintów
- **auth.py** - Logowanie i wylogowanie
- **users.py** - Zarządzanie użytkownikami (CRUD)
- **books.py** - Operacje na książkach (CRUD, ulubione)
- **libraries.py** - Zarządzanie bibliotekami
- **loans.py** - Zarządzanie wypożyczeniami i rezerwacjami
- **main.py** - Strona główna, powiadomienia, API, ustawienia języka

### app/utils/
Helpery i narzędzia:
- **decorators.py** - `@role_required` i inne dekoratory
- **notifications.py** - Tworzenie powiadomień
- **__init__.py** - Eksport funkcji utility

### app/templates/
Szablony zorganizowane w podfoldery:
```
templates/
├── base/
│   ├── layout.html
│   └── ... (komponenty bazowe)
├── auth/
│   └── login.html
├── users/
│   ├── users.html
│   ├── user_add.html
│   ├── user_edit.html
│   ├── user_profile.html
│   └── user_settings.html
├── books/
│   ├── book_detail.html
│   ├── book_add.html
│   └── book_edit.html
├── libraries/
│   ├── libraries.html
│   └── library_form.html
└── loans/
    ├── loans.html
    └── loan_add.html
```

### app/seeds/
Dane seed dla development i testowania:
- **seed.py** - Funkcja do inicjalizacji bazy danych
- **__init__.py** - Eksport seed_database()

Użycie:
```bash
python app/seeds/seed.py
```

### tests/
Folder na testy jednostkowe:
- Będą zawierać testy dla każdego modułu routes

### docs/
Dokumentacja projektu:
- API.md
- DATABASE.md
- DEVELOPMENT.md
- DEPLOYMENT.md

## Korzyści

1. **Lepszą organizacja kodu** - Każdy blueprint jest w oddzielnym pliku
2. **Łatwiejsze do utrzymania** - routes.py zmniejszony z 1099 linii do kilkuset
3. **Lepsze testy** - Łatwiej testować moduły niezależnie
4. **Skalowalnośc** - Łatwo dodawać nowe moduły (routes)
5. **Separacja odpowiedzialności** - Utils wydzielone od routów

## Migracja szablonów

Szablony będą stopniowo przenoszone do folderów podrzędnych. Aktualnie działają z wersji oryginalnej ścieżki.

## Import i użycie

### Rejestracja blueprintów
```python
from app.routes import register_blueprints
register_blueprints(app)
```

### Import narzędzi
```python
from app.utils import role_required, create_notification
```

### Seed database
```python
from app.seeds import seed_database
seed_database()
```

## Przyszłe ulepszenia

- [ ] Przenieść wszystkie szablony do podfoldery
- [ ] Dodać testy jednostkowe
- [ ] Dodać testy integracyjne
- [ ] Dokumentacja API (Swagger/OpenAPI)
- [ ] Docker compose dla łatwego deploymentu
