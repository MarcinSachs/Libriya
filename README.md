# Libriya

![Libriya logo](app/static/images/logo.svg)

Libriya is a lightweight multi-tenant library/catalog web application built with Flask. It provides tenant (subdomain) based libraries, user accounts, book cataloging, loans/reservations, cover-image fallbacks (OpenLibrary + optional premium provider), admin/audit features and a progressive-webapp-ready frontend.

Key features
- Multi-tenant architecture (subdomain-based routing)
- User registration, email verification and roles (admin / user)
- Book catalog with authors, genres and ISBN validation
- Cover image management with tiered fallbacks (Premium → OpenLibrary → local default)
- Loans, reservations and basic circulation workflows
- Background scheduler for maintenance tasks and cleanup CLI command
- Internationalization (Flask-Babel) with English/Polish locales
- Rate limiting, caching and configurable premium integrations
- Full pytest test-suite with unit and route tests

Technology stack
- Python + Flask
- SQLAlchemy (ORM) + Flask-Migrate (Alembic)
- WTForms, Flask-Login, Flask-Babel
- Optional Redis for rate-limiting / caching in production
- MariaDB (docker-compose config included) or SQLite for local development

Contents
- app/ — application package (models, forms, routes, services)
- migrations/ — Alembic migrations
- tests/ — pytest test-suite
- scripts/ — helper scripts (reset/seed, migration inspectors)
- docker/ & docker-compose.yml — MariaDB service for local development

Quick start (local development)
1. Clone repository
   git clone <repo>
   cd Libriya

2. Create and activate virtualenv (PowerShell):
   python -m venv .venv; .\.venv\Scripts\Activate

3. Install dependencies
   pip install -r requirements.txt

4. Create basic environment variables (create a `.env` file or export in shell)
   Example `.env`:
   SECRET_KEY=your-dev-secret
   DATABASE_URL=sqlite:///instance/libriya.db
   FLASK_ENV=development

   The app will default to a local SQLite DB if `DATABASE_URL` is not set.

5. Initialize database (Flask-Migrate already configured)
   flask --app libriya.py db upgrade

6. Run the app
   python libriya.py
   Open http://127.0.0.1:5001

Running with MariaDB (Docker)
- Start MariaDB (and phpMyAdmin) for local development:
  docker-compose up -d

- Reset & seed the database (Windows PowerShell helper included):
  .\scripts\reset_and_seed.ps1 -Yes

- Point the app to the running DB (set DATABASE_URL to a MariaDB URI)

Testing
- Run the full test-suite:
  pytest

- Run a single test file or test:
  pytest tests/test_subdomain_validators.py::test_validate_subdomain_field_normalizes_and_sets_data

Database migrations
- Create a new migration after model changes:
  flask --app libriya.py db migrate -m "describe change"
  flask --app libriya.py db upgrade

CLI / maintenance
- cleanup-notifications: Remove old read notifications
  flask --app libriya.py cleanup-notifications --days 60

Configuration (important env variables)
- SECRET_KEY (required)
- DATABASE_URL (defaults to SQLite in repository)
- FLASK_ENV (development | production)
- MAIL_SERVER / MAIL_PORT / MAIL_USERNAME / MAIL_PASSWORD (email)
- RATELIMIT_STORAGE_URL (set to Redis URL in production)
- PREMIUM_BOOKCOVER_ENABLED (toggle premium bookcover provider)
- ENFORCE_SUBDOMAIN_EXISTS (set False for local wildcard hosts)

Internationalization
- Translations live in `translations/`. Use the provided scripts to extract / compile messages:
  python scripts/extract_messages.py
  python scripts/compile_translations.py

Development notes
- The project is structured to keep service logic in `app/services` (OpenLibrary, cover, premium manager, cache helpers).
- Unit and route tests live under `tests/` and use fixtures from `tests/conftest.py`.
- The app uses subdomain routing middleware — when testing routes include `base_url=f'http://{subdomain}.example.com'`.

Contributing
- Contributions, bug reports and PRs are welcome. Please keep changes small and include tests for bug fixes / new features.

Further reading
- See `docs/models.md` for the data model overview
- See `tests/` for extensive examples of using fixtures, mocking external services and testing subdomain-based routes

If you want, I can also add a CONTRIBUTING.md, examples/.env.example, or CI/test workflow (GitHub Actions).

