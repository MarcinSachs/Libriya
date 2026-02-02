# Quick Start - MariaDB Setup

## Szybki Start z MariaDB

### 1. Uruchom MariaDB w Docker

```powershell
# Uruchom kontener
docker-compose up -d mariadb

# Sprawdź status
docker-compose ps

# Zobacz logi
docker-compose logs -f mariadb

# Opcjonalnie: uruchom phpMyAdmin
docker-compose up -d phpmyadmin
# Dostęp: http://localhost:8080
```

### 2. Skonfiguruj połączenie

Skopiuj `.env.example` do `.env` i edytuj:

```bash
# .env
SECRET_KEY=your-secret-key-here

# MariaDB connection
DATABASE_URL=mysql+pymysql://libriya_user:libriya_password_change_me@localhost:3306/libriya_db?charset=utf8mb4
```

**WAŻNE**: Hasło musi się zgadzać z tym w `docker-compose.yml`!

### 3. Zainstaluj zależności

```powershell
# Upewnij się, że masz aktywne wirtualne środowisko
pip install -r requirements.txt
```

### 4. Stwórz bazę danych (opcjonalnie)

```powershell
# Opcja 1: Automatycznie
python manage_db.py create-db

# Opcja 2: Ręcznie przez MySQL klienta
docker exec -it libriya_mariadb mysql -u root -p
# Hasło: root_password_change_me (z docker-compose.yml)
```

```sql
CREATE DATABASE IF NOT EXISTS libriya_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON libriya_db.* TO 'libriya_user'@'%';
FLUSH PRIVILEGES;
EXIT;
```

### 5. Uruchom migracje

```powershell
# Opcja 1: Użyj skryptu pomocniczego
python manage_db.py init

# Opcja 2: Standardowe komendy Flask
flask db upgrade
```

### 6. (Opcjonalnie) Załaduj dane testowe

```powershell
python -c "from app import create_app, db; from app.seeds.seed import seed_database; app = create_app(); app.app_context().push(); seed_database()"
```

### 7. Uruchom aplikację

```powershell
python libriya.py
```

## Sprawdzanie Statusu

```powershell
# Status bazy danych
python manage_db.py status

# Status migracji
flask db current
flask db heads

# Lista tabel
docker exec -it libriya_mariadb mysql -u libriya_user -p libriya_db -e "SHOW TABLES;"
```

## Typowe Problemy

### Problem: "Can't connect to MySQL server"

**Rozwiązanie**: 
```powershell
# Sprawdź czy kontener działa
docker-compose ps

# Sprawdź logi
docker-compose logs mariadb

# Restart kontenera
docker-compose restart mariadb
```

### Problem: "Access denied for user"

**Rozwiązanie**: Sprawdź czy hasło w `.env` zgadza się z `docker-compose.yml`

### Problem: "Unknown database 'libriya_db'"

**Rozwiązanie**:
```powershell
python manage_db.py create-db
```

## Backup i Restore

### Backup

```powershell
# Backup całej bazy
docker exec libriya_mariadb mysqldump -u libriya_user -plibriya_password_change_me libriya_db > backup.sql

# Backup z kompresją
docker exec libriya_mariadb mysqldump -u libriya_user -plibriya_password_change_me libriya_db | gzip > backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql.gz
```

### Restore

```powershell
# Z pliku SQL
docker exec -i libriya_mariadb mysql -u libriya_user -plibriya_password_change_me libriya_db < backup.sql

# Z skompresowanego pliku
gunzip < backup.sql.gz | docker exec -i libriya_mariadb mysql -u libriya_user -plibriya_password_change_me libriya_db
```

## Przełączanie między SQLite a MariaDB

### Z SQLite na MariaDB

1. Eksportuj dane ze SQLite (jeśli potrzebne)
2. Zmień `DATABASE_URL` w `.env`
3. Uruchom `flask db upgrade`
4. Importuj dane (jeśli potrzebne)

### Z MariaDB na SQLite (development)

1. Backup MariaDB
2. Zmień `DATABASE_URL` na `sqlite:///libriya.db`
3. Usuń `libriya.db` jeśli istnieje
4. Uruchom `flask db upgrade`

## Przydatne Komendy Docker

```powershell
# Zatrzymaj wszystko
docker-compose down

# Zatrzymaj i usuń volumes (UWAGA: usuwa dane!)
docker-compose down -v

# Zobacz logi
docker-compose logs -f mariadb

# Wejdź do kontenera
docker exec -it libriya_mariadb bash

# MySQL shell
docker exec -it libriya_mariadb mysql -u libriya_user -p
```

## Produkcja

Dla produkcji:

1. **Zmień hasła** w `docker-compose.yml` i `.env`
2. **Użyj external volumes** dla danych
3. **Skonfiguruj backup** (automatyczny)
4. **Monitoring** - połączenia, wolne zapytania
5. **Tuning** - dostosuj `innodb_buffer_pool_size` do RAM

Zobacz szczegóły w [DATABASE_MIGRATIONS.md](DATABASE_MIGRATIONS.md)
