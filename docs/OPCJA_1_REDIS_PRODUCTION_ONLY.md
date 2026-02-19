# Opcja 1: Redis Tylko na Production - Instrukcja Implementacji

## 📋 Podsumowanie Rozwiązania

```
DEVELOPMENT                    PRODUCTION
┌─────────────────┐            ┌─────────────────────┐
│ Flask App       │            │ Flask App (Gunicorn)│
├─────────────────┤            ├─────────────────────┤
│ Limiter         │            │ Limiter             │
│ └─ memory://    │            │ └─ redis://         │
└─────────────────┘            ├─────────────────────┤
      ↓                        │ Nginx reverse proxy │
   SQLite                       ├─────────────────────┤
                                │ Redis Server        │
NO REDIS NEEDED                 └─────────────────────┘
                                REDIS REQUIRED
```

---

## ✅ Co Zostało Zmienione

### 1. config.py

```python
# DODANO:
RATELIMIT_STORAGE_URL: Optional[str] = os.getenv('RATELIMIT_STORAGE_URL', None)

# Logika:
# - Jeśli RATELIMIT_STORAGE_URL jest ustawiony → Użyj Redisa (production)
# - Jeśli RATELIMIT_STORAGE_URL jest None → Użyj memory:// (development)
```

### 2. app/__init__.py

```python
# ZMIENIONO:
storage_url = app.config.get('RATELIMIT_STORAGE_URL')
if storage_url:
    limiter.init_app(app, key_func=get_remote_address, storage_uri=storage_url)
else:
    limiter.init_app(app, key_func=get_remote_address)  # memory:// default

# Logika:
# - Jeśli storage_url jest setowany → Inicjalizuj z Redis
# - Jeśli storage_url jest None → Inicjalizuj z memory (SimpleCache)
```

### 3. .env.production

```bash
# UPDATED:
RATELIMIT_STORAGE_URL=redis://:your_secure_password@redis.example.com:6379/1

# Zawiera przykłady i objaśnienia
```

### 4. .env.development (NOWY PLIK)

```bash
# Zawiera przykład dla deweloperów
# Ustawia RATELIMIT_STORAGE_URL jako NIEZDEFINIOWANY
```

---

## 🚀 Jak Zacząć

### Dla Deweloperów (Development)

```bash
# 1. Utwórz .env z .env.development
cp .env.development .env

# 2. Upewnij się że sekret jest ustawiony
# Edytuj .env i zmień SECRET_KEY

# 3. Zainstaluj aplikację (bez Redisa!)
pip install -r requirements.txt

# 4. Uruchom lokalnie
FLASK_ENV=development flask run

# 5. Testuj rate limiting
# - Będzie działać z memory:// (SimpleCache)
# - Każdy worker ma własny store (ale to OK na dev!)
```

### Dla Production

```bash
# 1. Zainstaluj Redis (z docs/REDIS_SETUP.md)
docker run -d \
  --name libriya-redis \
  -p 6379:6379 \
  redis:7-alpine \
  redis-server --requirepass "your_secure_password"

# 2. Zainstaluj redis client
pip install redis==5.0.1

# 3. Utwórz .env.production
cp .env.production .env

# 4. Ustawienia w .env.production:
RATELIMIT_STORAGE_URL=redis://:your_secure_password@redis.example.com:6379/1

# 5. Deployuj
gunicorn -w 4 -b 0.0.0.0:5000 libriya:app

# 6. Rate limiting teraz używa Redisa (bezpieczne dla multi-worker!)
```

---

## 🧪 Testowanie

### Development (bez Redisa)

```bash
# Terminal 1: Uruchom aplikację
FLASK_ENV=development flask run

# Terminal 2: Test rate limiting
for i in {1..10}; do
    curl http://localhost:5000/login/ -X POST \
        -d "username=test&password=test"
    echo "Request $i"
    sleep 0.5
done

# Expected: Po 5 żądaniach będzie rate limiting
# (rate limit: 5 per minute na login)
```

### Production (z Redisem)

```bash
# Sprawdzenie czy Redis działa
redis-cli ping
# Output: PONG

# Sprawdzenie czy limiter używa Redisa
redis-cli
> DBSIZE  # Powinno pokazać keys
> KEYS LIMITER_*  # Pokaż rate limit keys
> EXIT

# Test rate limiting
# Te same komendy co wyżej - ale teraz rate limits są shareowane
# między wszystkimi Gunicorn workerami
```

---

## 📊 Porównanie Konfiguracji

### Development (.env)
```bash
FLASK_ENV=development
RATELIMIT_STORAGE_URL=  # PUSTY/NIEZDEFINIOWANY
```

**Rezultat**:
- Rate limiter użyje `memory://`
- Dane w RAM aplikacji
- Nie potrzeba Redisa
- Każdy proces ma własne liczniki (OK na dev)

### Production (.env.production)
```bash
FLASK_ENV=production
RATELIMIT_STORAGE_URL=redis://:password@redis.example.com:6379/1
```

**Rezultat**:
- Rate limiter użyje Redisa
- Centralne liczniki (wszyscy workers widzą to samo)
- Musi być Redis running
- Bezpieczne dla multi-worker deploymentu

---

## ⚠️ Ważne Uwagi

### 1. Nie Zapomnij Redisa na Production!

```python
# ❌ BŁĄD - Production bez Redisa
FLASK_ENV=production
# RATELIMIT_STORAGE_URL nie ustawiony
# → Limiter użyje memory:// (nie skaluje się!)

# ✅ PRAWIDŁOWE
FLASK_ENV=production
RATELIMIT_STORAGE_URL=redis://localhost:6379/1
# → Limiter użyje Redisa (bezpieczne!)
```

### 2. Development może Nie Mieć Redisa

```bash
# ✅ OK - Development bez Redisa
FLASK_ENV=development
flask run
# → Automatycznie użyje memory://

# ⚠️ Alternatywa - Development z Redisem (dla testów)
FLASK_ENV=development
RATELIMIT_STORAGE_URL=redis://localhost:6379/1
docker run -d -p 6379:6379 redis:7-alpine
flask run
```

### 3. Zmiana .env Wymaga Restartu

```bash
# Zmienić RATELIMIT_STORAGE_URL w .env
# ↓
# Restart aplikacji!
FLASK_ENV=production flask run

# (Zmiana środowiska wymaga restartu)
```

---

## 🔧 Troubleshooting

### Redis Connection Error na Production

```bash
# ❌ Error: "Failed to connect to Redis"

# 1. Sprawdź czy Redis działa
redis-cli ping

# 2. Sprawdź RATELIMIT_STORAGE_URL
cat .env.production | grep RATELIMIT

# 3. Sprawdź czy hasło jest prawidłowe
redis-cli -h redis.example.com -a your_password ping

# 4. Sprawdź firewall
telnet redis.example.com 6379
```

### Rate Limiting Nie Działa na Production

```bash
# ❌ Wszyscy mogą robić unlimited żądań

# 1. Sprawdź czy aplikacja widzi RATELIMIT_STORAGE_URL
python -c "from config import Config; print(Config().RATELIMIT_STORAGE_URL)"

# 2. Sprawdź czy Gunicorn ma dostęp do Redis
gunicorn -w 4 -b 0.0.0.0:5000 libriya:app

# 3. Sprawdź Redis keys
redis-cli KEYS LIMITER_*

# 4. Jeśli brak → Limiter używa memory:// (zła konfiguracja!)
```

### Rate Limiting Działa, Ale Ma Różne Liczniki

```bash
# ❌ Worker 1 liczy 4/5, Worker 2 liczy 1/5 (powinno być wspólne)

# Powód: Development z memory:// (normalne)
# To jest OK na development!
# Jeśli na production → problem z RATELIMIT_STORAGE_URL

# Sprawdzenie:
echo $RATELIMIT_STORAGE_URL  # Powinno zwrócić redis://...
```

---

## 📝 Environment Variables

### Development (.env)

| Zmienna | Wartość | Opis |
|---------|---------|------|
| FLASK_ENV | development | Tryb dev |
| RATELIMIT_STORAGE_URL | (empty) | Użyj memory:// |
| DATABASE_URL | sqlite:///libriya.db | Lokalna DB |
| DEBUG | True | Debugger |

### Production (.env.production)

| Zmienna | Wartość | Opis |
|---------|---------|------|
| FLASK_ENV | production | Tryb prod |
| RATELIMIT_STORAGE_URL | redis://... | Centralne liczniki |
| DATABASE_URL | mysql://... | Zewnętrzna DB |
| DEBUG | False | No debugger |

---

## ✅ Checklist Before Production

- [ ] Redis installed and running
- [ ] RATELIMIT_STORAGE_URL configured in .env.production
- [ ] Requirements updated with redis==5.0.1
- [ ] Tested rate limiting works (redis-cli KEYS LIMITER_*)
- [ ] Gunicorn starts without Redis connection errors
- [ ] Rate limits consistent across all workers
- [ ] .env.production backup created
- [ ] .env.development used locally (no Redis)

---

## 📖 Dokumentacja Powiązana

- **docs/REDIS_SETUP.md** - Instalacja Redisa
- **docs/DEPLOYMENT_GUIDE.md** - Full deployment guide
- **config.py** - Pydantic konfiguracja
- **app/__init__.py** - Flask initialization

---

## 🎯 Następne Kroki

1. ✅ **Opcja 1 zaimplementowana** - Config i kod gotowy
2. ⏭️ **Aktualizuj requirements.txt** - Dodaj redis==5.0.1
3. ⏭️ **Setup Redis na production** - Użyj docs/REDIS_SETUP.md
4. ⏭️ **Test lokalnie** - `FLASK_ENV=development flask run`
5. ⏭️ **Deploy na production** - Ustaw RATELIMIT_STORAGE_URL

---

**Status**: ✅ READY FOR IMPLEMENTATION  
**Last Updated**: 2026-02-19  
**Next**: Update requirements.txt with redis package
