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
*   **ISBN Lookup:** Integration with OpenLibrary API to fetch book data by ISBN.
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

## To Do

*   **Enhance Internationalization:**
    *   Add more languages.
    *   Complete translations for existing languages.
    *   Implement more robust language switching.

*   **Improve User Interface:**
    *   Add better error handling and user feedback.

*   **Add Advanced Features:**
    *   Implement a system for managing fines.
    *   Add a book recommendation system.
    *   Implement an "archive" feature for books with loan history instead of deleting them

*   **Testing:**
    *   Write unit tests and integration tests to ensure code quality.

*   **Deployment:**
    *   Prepare the application for deployment to a production environment.

*   **Code Refactoring:**
    *   Review and refactor the code for better maintainability and performance.
    *   Improve documentation.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## License

MIT License
