# Libriya
![alt text](app/static/images/logo.svg)

Libriya is a web application for managing a library, built with Flask, SQLAlchemy, and other Python packages.

**Please Note: This project is still under development and is not yet feature-complete.**

[Live Demo](https://marcins.pythonanywhere.com)

## Features (Implemented/Planned)

*   **Book Management:** Add, edit, and delete books from the library.
*   **Book Location Tracking:** Store structured location information (shelf, section, room, notes) for each book.
*   **Author and Genre Management:** Automatically create and manage authors and genres associated with books.
*   **User Authentication:** User login, registration with invitation codes, and logout.
*   **Admin Privileges:** Admin users can manage users, books, and generate invitation codes.
*   **Book Loans:** Track which books are currently borrowed and by whom.
*   **User Profiles:** Users can view their loan history.
*   **User Settings:** Users can edit their profile and settings.
*   **Internationalization (i18n):** Full support for multiple languages (currently English and Polish).
*   **ISBN Lookup:** Integration with Biblioteka Narodowa (BN) and OpenLibrary APIs to fetch book data by ISBN.
*   **ISBN Scanner with OCR:** Mobile camera-based scanner that reads:
    - Traditional QR/barcode codes
    - Printed ISBN numbers via optical character recognition (OCR)
*   **Book Cover Management:** Automatic cover retrieval with intelligent fallback system:
    - Biblioteka Narodowa (Polish National Library) - primary source for Polish books
    - Open Library - fallback when primary source lacks cover images
    - Bookcover API (Goodreads) - secondary fallback
    - Local caching of external cover images
*   **MARC Record Support:** Extraction of book metadata from MARC records when top-level fields are incomplete.
*   **Comments:** Users can add comments to books.
*   **Favorites:** Users can add books to their favorites list.
*   **Notifications:**  Users and administrators receive notifications about loan requests, approvals, cancellations, and overdue reminders.
*   **Audit Logging:** Administrative actions are logged for security and compliance.

## Setup

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/MarcinSachs/Libriya.git
    cd libriya
    ```

2.  **Create a virtual environment:**

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Linux/macOS
    # venv\Scripts\activate  # On Windows
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure the application:**

    *   Set environment variables (see `config.py` for available options). A `.flaskenv` file can be used. For example:

        ```
        FLASK_APP=libriya.py
        FLASK_ENV=development
        SECRET_KEY=your_secret_key
        ```

    *   If you don't set `DATABASE_URL`, a SQLite database (`libriya.db`) will be created in the project directory.

5.  **Initialize the database:**

    ```bash
    flask db init
    flask db migrate -m "Initial migration"
    flask db upgrade
    ```

6.  **Run the application:**

    ```bash
    flask run
    ```

## Recent Improvements (v2.0)

### ISBN Scanner with OCR Recognition
- **Dual-Mode Barcode Scanning:** 
  - Traditional QR/barcode scanning (html5-qrcode library)
  - **NEW:** OCR text recognition for printed ISBN numbers
- **Backend OCR Processing:**
  - Powered by EasyOCR (pure Python, no system dependencies)
  - Works on Windows, Linux, and server environments
  - Intelligent image preprocessing (contrast enhancement, thresholding)
  - Multiple recognition strategies for reliability
- **ISBN Extraction:**
  - Detects both ISBN-10 (with/without dashes) and ISBN-13 formats
  - Recognizes patterns like "83-225-0046-7"
  - Optimized for fast detection (300ms frame interval)
- **Seamless Integration:**
  - Auto-searches for book when ISBN is detected
  - Works on mobile devices with camera access
  - Responsive visual feedback (green highlight on detection)

### ISBN Search & Cover Retrieval Enhancement
- **Dual API Integration:** Searches Biblioteka Narodowa first, then falls back to Open Library
- **Intelligent Cover Management:** 
  - Prioritizes covers from data source (Open Library)
  - Falls back to Open Library by ISBN when primary source lacks cover
  - Attempts Bookcover API (Goodreads) as secondary fallback
  - Uses local default image if no cover found
- **MARC Record Extraction:** Extracts metadata (title, author, publisher, year) from MARC records when top-level fields are empty or incomplete
- **Newest Record Selection:** Automatically selects the most recently created record when multiple editions exist for the same ISBN
- **Title Cleanup:** Removes trailing punctuation and whitespace for cleaner metadata

### UI/UX Improvements
- **File Input Localization:** Proper translation of file input controls ("Browse...", "No file selected")
- **Temporary File Cleanup:** Automatic cleanup of cover images when users cancel book addition
- **Enhanced Form Styling:** Custom styled file input with proper internationalization support

## Testing

The application includes comprehensive testing:
- Unit tests for ISBN validation and book search services
- Integration tests for API endpoints
- Test coverage for MARC record parsing
- Cover retrieval fallback chain testing

Run tests with:
```bash
pytest tests/
```

## Architecture

### Book Search Pipeline
1. **ISBN Input** → Validation
2. **Biblioteka Narodowa Search** → MARC extraction if needed
3. **Open Library Fallback** → If BN search fails
4. **Cover Retrieval** → Multi-source with intelligent fallbacks
5. **Result Caching** → Store book data with cover images locally

### Database Structure
- **Books:** Title, ISBN, author, publisher, year, location tracking
- **Authors:** Auto-managed from book data
- **Genres:** Category management
- **Loans:** Tracking borrowed books with status workflow
- **Users:** User management with roles (user, librarian, admin)
- **Notifications:** System notifications for loans and requests
- **Audit Logs:** Administrative action tracking

## API Endpoints

### Book Search
- `GET /api/v1/isbn/<isbn>` - Search book by ISBN (includes cover data)
- `GET /api/v1/search/title` - Search books by title
- `POST /api/v1/ocr/isbn` - Extract ISBN from image via OCR (mobile scanner)

### Book Management
- `GET /api/books` - List all books (with location filtering)
- `POST /api/books` - Add new book
- `GET /api/books/<id>` - Get book details
- `PUT /api/books/<id>` - Update book
- `DELETE /api/books/<id>` - Delete book

## Configuration

See `config.py` for available configuration options:
- `DATABASE_URL` - Database connection string
- `SECRET_KEY` - Flask secret key
- `UPLOAD_FOLDER` - Location for uploaded cover images
- `MAX_COVER_SIZE` - Maximum cover image size (default: 5MB)
- `LANGUAGES` - Supported languages (default: ['en', 'pl'])

### OCR Configuration

The ISBN scanner uses **EasyOCR** for optical character recognition:
- **Pure Python implementation** - No system dependencies required (unlike Tesseract)
- **Works everywhere:** Windows, Linux, macOS, and server environments
- **First-time setup:** Downloads recognition model (~200MB) automatically on first use
- **Subsequent runs:** Model cached locally for instant startup
- **Performance:** Optimized for CPU-only systems with reduced thread usage

## Crowdin Integration

This project uses [Crowdin](https://crowdin.com/) for translation management with automatic GitHub synchronization.

**✅ FREE PLAN INCLUDES FULL API ACCESS** - Unlike some alternatives, Crowdin's free plan provides complete API access and GitHub integration.

**📖 See [CROWDIN_SETUP.md](CROWDIN_SETUP.md) for detailed setup instructions.**

### Quick Setup Summary

1. **Create a Crowdin account** and project at [crowdin.com](https://crowdin.com)

2. **Get your credentials:**
   - **Personal Access Token:** Generate in Crowdin under *Settings → API*
   - **Project ID:** Found in your project URL or settings

3. **Add GitHub Secrets:**
   - Go to your repository *Settings → Secrets and variables → Actions*
   - Add the following secrets:
     - `CROWDIN_PERSONAL_TOKEN` - Your Crowdin personal access token
     - `CROWDIN_PROJECT_ID` - Your Crowdin project ID

4. **Configure GitHub Integration in Crowdin:**
   - Go to *Integrations → GitHub* in your Crowdin project
   - Connect your repository and configure the sync settings
   - Point to the `crowdin.yml` configuration file in the repository root

### How It Works

Crowdin provides native GitHub integration with automatic bidirectional sync:

- **GitHub → Crowdin:** When you push changes to translation source files, Crowdin automatically imports them
- **Crowdin → GitHub:** When translations are updated, Crowdin creates a pull request automatically

No GitHub Actions workflows needed - everything is handled by Crowdin's integration!

### Working with Translations

1. **Extract new strings:**
   ```bash
   pybabel extract -F babel.cfg -o translations/messages.pot .
   ```

2. **Update existing translations:**
   ```bash
   pybabel update -i translations/messages.pot -d translations
   ```

3. **Compile translations locally:**
   ```bash
   python compile_translations.py
   # or
   pybabel compile -d translations
   ```

4. **Push changes:** Commit and push to `main` - Crowdin automatically syncs within minutes

5. **Get translations:** Crowdin automatically creates a PR when translations are updated

For more details, troubleshooting, and advanced configuration, see [CROWDIN_SETUP.md](CROWDIN_SETUP.md).

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

### Development Setup
1. Install development dependencies: `pip install -r requirements.txt`
2. Set up pre-commit hooks for code quality
3. Write tests for new features
4. Ensure all tests pass before submitting PR

## Known Issues & Limitations

- Some Polish National Library records may have incomplete metadata
- Cover images depend on external API availability
- Demo instance may have rate limiting on external APIs

## Roadmap

- [ ] Advanced search filters (date range, author, publisher)
- [ ] Book recommendation system
- [ ] Fine management system
- [ ] Book archive feature (preserve history instead of deletion)
- [ ] Mobile app / Progressive Web App (PWA)
- [ ] Extended language support
- [ ] Performance optimization for large libraries

## License

MIT License

