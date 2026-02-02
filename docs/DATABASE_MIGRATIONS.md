# Migracje Bazy Danych - Dokumentacja

## Przegląd

Projekt Libriya używa **Alembic** z **Flask-Migrate** do zarządzania migracjami bazy danych. To rozwiązanie jest:
- ✅ Stabilne i sprawdzone w produkcji
- ✅ Wspiera wszystkie główne bazy danych (SQLite, MySQL, MariaDB, PostgreSQL)
- ✅ Umożliwia bezpieczne zmiany schematu bez utraty danych
- ✅ Pozwala na rollback zmian w razie problemów
- ✅ Wersjonuje zmiany w bazie danych jak kod w Git

## Konfiguracja Środowisk

### Development (SQLite)
```bash
DATABASE_URL=sqlite:///libriya.db
```

### Production (MariaDB)
```bash
DATABASE_URL=mysql+pymysql://libriya_user:password@localhost:3306/libriya_db?charset=utf8mb4
```

### Docker MariaDB
```bash
# Uruchom bazę danych
docker-compose up -d mariadb

# Sprawdź status
docker-compose ps

# Logi
docker-compose logs -f mariadb
```

## Podstawowe Komendy

### Inicjalizacja (tylko raz, już zrobione)
```bash
flask db init
```

### Tworzenie Nowej Migracji

#### Automatyczna migracja (zalecane)
```bash
# Generuje migrację na podstawie zmian w modelach
flask db migrate -m "Opis zmian"
```

#### Pusta migracja (dla własnych zmian)
```bash
flask db revision -m "Opis zmian"
```

### Stosowanie Migracji

```bash
# Zastosuj wszystkie pending migrations
flask db upgrade

# Zastosuj do konkretnej wersji
flask db upgrade <revision_id>

# Cofnij ostatnią migrację
flask db downgrade -1

# Cofnij do konkretnej wersji
flask db downgrade <revision_id>
```

### Sprawdzanie Statusu

```bash
# Aktualna wersja bazy
flask db current

# Historia migracji
flask db history

# Pokaż pending migrations
flask db heads

# Pokaż szczegóły migracji
flask db show <revision_id>
```

## Best Practices - WAŻNE! 🚨

### 1. Zawsze Sprawdzaj Wygenerowaną Migrację

```bash
# Po wygenerowaniu migracji ZAWSZE przejrzyj plik:
cat migrations/versions/<filename>.py
```

Autogenerate nie jest idealne i może:
- Nie wykryć wszystkich zmian (np. zmiana nazw tabel/kolumn)
- Wygenerować niepotrzebne operacje
- Nie obsłużyć złożonych zmian

### 2. Testuj Migracje

```bash
# 1. Zrób backup bazy
# 2. Zastosuj migrację
flask db upgrade

# 3. Testuj aplikację
# 4. Sprawdź czy rollback działa
flask db downgrade -1

# 5. Zastosuj ponownie
flask db upgrade
```

### 3. Bezpieczne Migracje Produkcyjne

#### Przed Migracją
1. **Backup bazy danych**
   ```bash
   # MariaDB
   docker exec libriya_mariadb mysqldump -u libriya_user -p libriya_db > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Sprawdź pending migrations**
   ```bash
   flask db current
   flask db heads
   ```

3. **Testuj na kopii produkcyjnej bazy**

#### Podczas Migracji
1. **Włącz tryb maintenance** (opcjonalnie)
2. **Zastosuj migrację**
   ```bash
   flask db upgrade
   ```
3. **Zweryfikuj poprawność**
4. **Wyłącz maintenance mode**

#### Po Migracji
1. Sprawdź logi aplikacji
2. Zweryfikuj kluczowe funkcje
3. Monitoruj wydajność

### 4. Przykłady Bezpiecznych Migracji

#### Dodawanie Kolumny z Wartością Domyślną
```python
def upgrade():
    # Dobra praktyka: nullable=True najpierw
    op.add_column('books', sa.Column('rating', sa.Integer(), nullable=True))
    
    # Wypełnij istniejące rekordy
    op.execute('UPDATE books SET rating = 0 WHERE rating IS NULL')
    
    # Teraz można zmienić na NOT NULL
    op.alter_column('books', 'rating', nullable=False)

def downgrade():
    op.drop_column('books', 'rating')
```

#### Zmiana Nazwy Kolumny
```python
def upgrade():
    # Alembic może nie wykryć zmiany nazwy - trzeba ręcznie określić
    op.alter_column('books', 'old_column_name', new_column_name='new_column_name')

def downgrade():
    op.alter_column('books', 'new_column_name', new_column_name='old_column_name')
```

#### Dodawanie Foreign Key z Istniejącymi Danymi
```python
def upgrade():
    # 1. Dodaj kolumnę nullable
    op.add_column('books', sa.Column('author_id', sa.Integer(), nullable=True))
    
    # 2. Wypełnij danymi (np. domyślnym autorem)
    op.execute('UPDATE books SET author_id = 1 WHERE author_id IS NULL')
    
    # 3. Dodaj foreign key constraint
    op.create_foreign_key('fk_books_author', 'books', 'authors', ['author_id'], ['id'])
    
    # 4. Zmień na NOT NULL
    op.alter_column('books', 'author_id', nullable=False)
```

### 5. Obsługa Różnych Baz Danych

```python
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Sprawdź typ bazy danych
    conn = op.get_bind()
    if conn.dialect.name == 'sqlite':
        # SQLite nie wspiera DROP COLUMN bez recreate
        # Użyj batch mode (już skonfigurowane w env.py)
        with op.batch_alter_table('books') as batch_op:
            batch_op.drop_column('old_column')
    else:
        # MySQL/MariaDB/PostgreSQL
        op.drop_column('books', 'old_column')
```

### 6. Długie Migracje (Duże Tabele)

```python
def upgrade():
    # Dla dużych tabel, użyj batch updates
    conn = op.get_bind()
    
    # Zamiast: UPDATE books SET status = 'available'
    # Użyj batch:
    batch_size = 1000
    conn.execute("""
        UPDATE books 
        SET status = 'available' 
        WHERE id IN (
            SELECT id FROM books 
            WHERE status IS NULL 
            LIMIT :batch_size
        )
    """, {"batch_size": batch_size})
```

## Rozwiązywanie Problemów

### Problem: Migracja się nie wykonuje

```bash
# Sprawdź aktualną wersję
flask db current

# Sprawdź czy są konflikty
flask db heads

# Jeśli masz wiele heads (rozgałęzienie):
flask db merge -m "Merge heads" <revision1> <revision2>
```

### Problem: Błąd podczas migracji

```bash
# 1. Cofnij ostatnią migrację
flask db downgrade -1

# 2. Popraw plik migracji w migrations/versions/

# 3. Zastosuj ponownie
flask db upgrade
```

### Problem: Baza jest w nieznanym stanie

```bash
# UWAGA: To nadpisze aktualny stamp
# Użyj tylko gdy jesteś pewien aktualnego stanu bazy

# Oznacz bazę jako określoną wersję (bez wykonywania migracji)
flask db stamp <revision_id>

# Lub jako head (najnowsza)
flask db stamp head
```

## Migracja z SQLite do MariaDB

### Krok 1: Eksport Danych
```bash
# Użyj narzędzia do konwersji
pip install mysql-connector-python

# Lub użyj skryptu exportu/importu (trzeba napisać)
python scripts/export_data.py
```

### Krok 2: Nowa Baza MariaDB
```bash
# 1. Uruchom MariaDB
docker-compose up -d mariadb

# 2. Zmień DATABASE_URL w .env
DATABASE_URL=mysql+pymysql://libriya_user:password@localhost:3306/libriya_db?charset=utf8mb4

# 3. Stwórz tabele
flask db upgrade

# 4. Importuj dane
python scripts/import_data.py
```

## Monitoring i Maintenance

### Regularne Zadania

1. **Backup przed każdą migracją produkcyjną**
2. **Przegląd migracji** - usuwaj stare/nieużywane branches
3. **Testuj rollback** - upewnij się, że downgrade działa
4. **Dokumentuj złożone migracje** - dodaj komentarze w plikach migracji

### Logi Migracji

```python
# W env.py możesz zwiększyć poziom logowania:
logger.setLevel(logging.DEBUG)
```

## Dodatkowe Zasoby

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Flask-Migrate Documentation](https://flask-migrate.readthedocs.io/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [MySQL/MariaDB Migration Best Practices](https://dev.mysql.com/doc/refman/8.0/en/migration.html)

## Checklist przed Produkcją

- [ ] Wszystkie migracje przetestowane lokalnie
- [ ] Migracje przetestowane na kopii produkcyjnej bazy
- [ ] Backup produkcyjnej bazy wykonany
- [ ] Rollback plan przygotowany
- [ ] Monitoring włączony
- [ ] Czas maintenance zaplanowany (jeśli potrzebny)
- [ ] Team poinformowany o zmianach
