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

