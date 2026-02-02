# Checklist przed Wdrożeniem Produkcyjnym

## Bezpieczeństwo

- [ ] **Zmieniono wszystkie domyślne hasła**
  - [ ] `SECRET_KEY` w `.env` (użyj `python -c "import secrets; print(secrets.token_hex(32))"`)
  - [ ] Hasła MariaDB w `docker-compose.yml`
  - [ ] Hasło root MariaDB
  - [ ] Hasło użytkownika MariaDB

- [ ] **Konfiguracja HTTPS**
  - [ ] Certyfikat SSL zainstalowany
  - [ ] HTTP przekierowane na HTTPS
  - [ ] HSTS włączone

- [ ] **Ustawienia Flask**
  - [ ] `FLASK_ENV=production`
  - [ ] `DEBUG=False`
  - [ ] `TESTING=False`

## Baza Danych

- [ ] **MariaDB skonfigurowane**
  - [ ] Połączenie działa
  - [ ] `DATABASE_URL` poprawnie ustawione w `.env`
  - [ ] Charset ustawiony na `utf8mb4`
  - [ ] Pool connections skonfigurowany

- [ ] **Migracje**
  - [ ] Wszystkie migracje zastosowane (`flask db upgrade`)
  - [ ] Sprawdzono `flask db current` - baza na najnowszej wersji
  - [ ] Przetestowano rollback na środowisku testowym

- [ ] **Backup**
  - [ ] System backupów skonfigurowany
  - [ ] Backupy testowane (restore działa)
  - [ ] Backupy przechowywane w bezpiecznym miejscu
  - [ ] Automatyczne backupy zaplanowane (cron/task scheduler)

- [ ] **Performance**
  - [ ] Indeksy w bazie sprawdzone
  - [ ] Slow query log włączony i monitorowany
  - [ ] Connection pool size dostosowany do obciążenia
  - [ ] `innodb_buffer_pool_size` dostosowane do RAM

## Docker & Infrastruktura

- [ ] **Docker Compose**
  - [ ] External volumes dla danych
  - [ ] Restart policy: `unless-stopped` lub `always`
  - [ ] Resource limits ustawione (CPU, pamięć)
  - [ ] Networking security skonfigurowane

- [ ] **Persistence**
  - [ ] Volumes dla danych MariaDB
  - [ ] Volumes dla uploads (okładki)
  - [ ] Volumes dla logów

## Monitoring & Logi

- [ ] **Logi**
  - [ ] Folder `logs/` istnieje i ma odpowiednie uprawnienia
  - [ ] Log rotation skonfigurowany
  - [ ] Logi MariaDB dostępne i monitorowane

- [ ] **Monitoring**
  - [ ] Health checks skonfigurowane
  - [ ] Alerting na błędy krytyczne
  - [ ] Monitorowanie wykorzystania zasobów

## Aplikacja

- [ ] **Konfiguracja**
  - [ ] Wszystkie zmienne w `.env` ustawione
  - [ ] `UPLOAD_FOLDER` istnieje i ma uprawnienia
  - [ ] `MAX_CONTENT_LENGTH` odpowiedni dla use case
  - [ ] Timezone ustawiony poprawnie

- [ ] **Testy**
  - [ ] Testy jednostkowe przechodzą (`pytest`)
  - [ ] Testy integracyjne przechodzą
  - [ ] Testy na środowisku staging przeszły

- [ ] **Dependencies**
  - [ ] `requirements.txt` aktualne
  - [ ] Wszystkie pakiety zainstalowane
  - [ ] Kompatybilność wersji sprawdzona

## Wydajność

- [ ] **Optymalizacja**
  - [ ] Static files serwowane przez nginx/CDN
  - [ ] Kompresja włączona (gzip)
  - [ ] Browser caching skonfigurowany
  - [ ] Database connection pooling włączone

- [ ] **PWA**
  - [ ] Service Worker działa
  - [ ] Manifest poprawnie skonfigurowany
  - [ ] Cache strategy odpowiednia

## Backup & Recovery

- [ ] **Procedury**
  - [ ] Procedura backup udokumentowana
  - [ ] Procedura restore przetestowana
  - [ ] Disaster recovery plan istnieje
  - [ ] RTO i RPO zdefiniowane

- [ ] **Automatyzacja**
  - [ ] Daily backup automatyczny
  - [ ] Retention policy zdefiniowana
  - [ ] Backup verification automatyczna

## Dokumentacja

- [ ] **Dla zespołu**
  - [ ] README.md aktualne
  - [ ] Instrukcje deployment
  - [ ] Kontakt do odpowiedzialnych osób
  - [ ] Procedury awaryjne

- [ ] **Dla użytkowników**
  - [ ] Instrukcja użytkowania
  - [ ] FAQ jeśli potrzebne
  - [ ] Informacja o wsparciu

## Pre-deployment

- [ ] **Ostatnie sprawdzenia**
  - [ ] Wszystkie TODO w kodzie zamknięte/udokumentowane
  - [ ] Żadnych credentials w kodzie
  - [ ] `.gitignore` poprawnie skonfigurowany
  - [ ] Wersja tagowana w Git

- [ ] **Rollback plan**
  - [ ] Procedura rollback udokumentowana
  - [ ] Backup przed deployment
  - [ ] Możliwość szybkiego powrotu do poprzedniej wersji

## Post-deployment

- [ ] **Weryfikacja**
  - [ ] Aplikacja startuje poprawnie
  - [ ] Logowanie działa
  - [ ] Kluczowe funkcje działają
  - [ ] Baza danych odpowiada
  - [ ] Logi bez błędów krytycznych

- [ ] **Monitoring**
  - [ ] Pierwsze 24h pod obserwacją
  - [ ] Metryki zbierane
  - [ ] Performance w normie
  - [ ] Użytkownicy mogą korzystać

---

## Przydatne Komendy

```powershell
# Sprawdź wersję migracji
flask db current

# Backup przed deployment
docker exec libriya_mariadb mysqldump -u libriya_user -p libriya_db > pre_deploy_backup.sql

# Zastosuj migracje
flask db upgrade

# Restart aplikacji
docker-compose restart app

# Sprawdź logi
docker-compose logs -f app
docker-compose logs -f mariadb
```

## Kontakty Awaryjne

- Database Admin: _______________
- DevOps: _______________
- Application Owner: _______________

---

Data przeglądu: __________
Osoba odpowiedzialna: __________
