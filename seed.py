from app.models import Genre, Library, User
from app import create_app, db
import sys
import os
from flask_babel import _

# Dodaj ścieżkę do katalogu projektu do sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))


genres = [
    _('Action'),
    _('Adventure'),
    _('Alternate History'),
    _('Animals'),
    _('Anime'),
    _('Anthology'),
    _('Art'),
    _('Autobiography'),
    _('Biography'),
    _('Business'),
    _('Cars'),
    _('Chick Lit'),
    _('Children\'s'),
    _('Christian Fiction'),
    _('Classics'),
    _('Comics'),
    _('Contemporary'),
    _('Cookbook'),
    _('Crafts'),
    _('Crime'),
    _('Dance'),
    _('Drama'),
    _('Dystopian'),
    _('Education'),
    _('Environment'),
    _('Epic Fantasy'),
    _('Erotic'),
    _('Fable'),
    _('Fairy Tale'),
    _('Family Saga'),
    _('Fantasy'),
    _('Food'),
    _('Gardening'),
    _('Gothic'),
    _('Graphic Novel'),
    _('Guide'),
    _('Health'),
    _('Historical'),
    _('Historical Fiction'),
    _('Home Improvement'),
    _('Horror'),
    _('Humor'),
    _('Inspirational'),
    _('Journal'),
    _('Languages'),
    _('Legal'),
    _('LGBTQ+'),
    _('Literary Fiction'),
    _('Magic'),
    _('Medical'),
    _('Memoir'),
    _('Military'),
    _('Music'),
    _('Mystery'),
    _('Mythology'),
    _('Nature'),
    _('New Adult'),
    _('Painting'),
    _('Parenting'),
    _('Philosophy'),
    _('Picture Book'),
    _('Poetry'),
    _('Political'),
    _('Psychology'),
    _('Reference'),
    _('Relationships'),
    _('Religion'),
    _('Review'),
    _('Romance'),
    _('Satire'),
    _('Science'),
    _('Science Fiction'),
    _('Self-Help'),
    _('Short Story'),
    _('Social Science'),
    _('Sociology'),
    _('Space'),
    _('Spirituality'),
    _('Sports'),
    _('Technology'),
    _('Thriller'),
    _('Travel'),
    _('Travel Guide'),
    _('True Crime'),
    _('True Story'),
    _('War'),
    _('Western'),
    _('Young Adult')
]


def seed_database():
    app = create_app()  # Utwórz instancję aplikacji
    with app.app_context():
        # --- Seed Library ---
        if db.session.query(Library).count() == 0:
            default_library = Library(name="Główna Biblioteka")
            db.session.add(default_library)
            db.session.commit()
            print("Default library created.")
        else:
            default_library = db.session.query(Library).first()
            print("Default library already exists.")

        # --- Seed Admin User ---
        if db.session.query(User).filter_by(username='admin').count() == 0:
            admin_user = User(
                username='admin',
                email='admin@example.com',
                role='admin'
            )
            admin_user.set_password('admin')
            # Add user to the default library
            admin_user.libraries.append(default_library)
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user created and assigned to the default library.")
        else:
            print("Admin user already exists.")

        # --- Seed Genres ---
        # Usuń wszystkie istniejące gatunki, aby uniknąć duplikatów
        db.session.query(Genre).delete()
        db.session.commit()
        print("Genre table cleared.")

        # Dodaj nowe gatunki z listy
        for genre_name in genres:
            genre = Genre(name=str(genre_name)) # Użyj str(), aby rozwiązać proxy z Babela
            db.session.add(genre)
        db.session.commit()
        print("Genres added to the database.")


if __name__ == '__main__':
    seed_database()
