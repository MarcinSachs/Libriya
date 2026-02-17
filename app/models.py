from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import datetime


class Tenant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    subdomain = db.Column(db.String(100), unique=True, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    status = db.Column(db.String(50), default='active', nullable=False)

    # Premium features - tenant-specific
    premium_bookcover_enabled = db.Column(db.Boolean, default=False, nullable=False)
    premium_biblioteka_narodowa_enabled = db.Column(db.Boolean, default=False, nullable=False)

    libraries = db.relationship('Library', backref='tenant', lazy=True)
    users = db.relationship('User', backref='tenant', lazy=True)

    def __str__(self):
        return f"{self.name} ({self.subdomain})"

    def get_enabled_premium_features(self):
        """Return list of enabled premium features for this tenant."""
        features = []
        if self.premium_bookcover_enabled:
            features.append('bookcover_api')
        if self.premium_biblioteka_narodowa_enabled:
            features.append('biblioteka_narodowa')
        return features

    def is_premium_enabled(self, feature_id):
        """Check if a specific premium feature is enabled for this tenant."""
        feature_map = {
            'bookcover_api': 'premium_bookcover_enabled',
            'biblioteka_narodowa': 'premium_biblioteka_narodowa_enabled',
        }
        field_name = feature_map.get(feature_id)
        if field_name:
            return getattr(self, field_name, False)
        return False


# Define the association table for book-author relationship
book_authors = db.Table('book_authors',
                        db.Column('book_id', db.Integer, db.ForeignKey(
                            'book.id'), primary_key=True),
                        db.Column('author_id', db.Integer, db.ForeignKey(
                            'author.id'), primary_key=True)
                        )
# Define the association table for book-genre relationship (NEW)
book_genres = db.Table('book_genres',
                       db.Column('book_id', db.Integer, db.ForeignKey(
                           'book.id'), primary_key=True),
                       db.Column('genre_id', db.Integer, db.ForeignKey(
                           'genre.id'), primary_key=True)
                       )

# Define the association table for favorites
favorites = db.Table('favorites',
                     db.Column('user_id', db.Integer, db.ForeignKey(
                         'user.id'), primary_key=True),
                     db.Column('book_id', db.Integer, db.ForeignKey(
                         'book.id'), primary_key=True)
                     )

# Define the association table for user-library relationship
user_libraries = db.Table('user_libraries',
                          db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
                          db.Column('library_id', db.Integer, db.ForeignKey('library.id'), primary_key=True)
                          )


class Library(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=False)
    books = db.relationship('Book', back_populates='library', lazy=True)
    users = db.relationship('User', secondary=user_libraries, lazy='subquery',
                            back_populates='libraries')
    loan_overdue_days = db.Column(db.Integer, nullable=False, default=14)

    def __str__(self):
        return self.name


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    library_id = db.Column(db.Integer, db.ForeignKey('library.id'), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=False)
    isbn = db.Column(db.String(13), unique=True, nullable=True, index=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    authors = db.relationship(
        'Author', secondary=book_authors, lazy='subquery', back_populates='books')

    # Relationship for multiple genres
    genres = db.relationship(
        'Genre', secondary=book_genres, lazy='subquery', back_populates='books')

    library = db.relationship('Library', back_populates='books')
    location = db.relationship('Location', back_populates='book', uselist=False, cascade='all, delete-orphan')

    year = db.Column(db.Integer, nullable=False)
    cover = db.Column(db.String(200))
    description = db.Column(db.Text, nullable=True)
    # 'available', 'reserved', 'on_loan'
    status = db.Column(db.String(50), default='available', nullable=False)

    comments = db.relationship('Comment', back_populates='book', lazy=True, cascade='all, delete-orphan')

    def __str__(self):
        author_names = ", ".join([author.name for author in self.authors])
        genre_names = ", ".join([genre.name for genre in self.genres])
        return f"{self.title} by {author_names} ({self.year}) - Genres: {genre_names}"


class Location(db.Model):
    """Book location information (shelf, section, room, etc.)"""
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False, unique=True)
    shelf = db.Column(db.String(50), nullable=True)  # e.g., "A", "B-1"
    section = db.Column(db.String(100), nullable=True)  # e.g., "Fiction", "Science"
    room = db.Column(db.String(100), nullable=True)  # e.g., "Main Hall", "Room 2"
    notes = db.Column(db.String(255), nullable=True)  # Additional info

    book = db.relationship('Book', back_populates='location')

    def __str__(self):
        parts = []
        if self.room:
            parts.append(self.room)
        if self.section:
            parts.append(self.section)
        if self.shelf:
            parts.append(f"Shelf {self.shelf}")
        if self.notes:
            parts.append(f"({self.notes})")
        return ", ".join(parts) if parts else "No location"


class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    books = db.relationship('Book', secondary=book_authors,
                            lazy='subquery', back_populates='authors')

    def __str__(self):
        return self.name


class Genre(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, index=True)
    books = db.relationship('Book', secondary=book_genres,
                            lazy='subquery', back_populates='genres')

    def __str__(self):
        return self.name


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True,
                         nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)  # INCREASED from 128 to 255 to accommodate PBKDF2 hashes
    image_file = db.Column(db.String(20), nullable=False,
                           default='default.jpg')
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    loans = db.relationship('Loan', back_populates='user', lazy=True)
    role = db.Column(db.String(20), nullable=False, default='user')  # 'user', 'manager', 'admin'
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=True)  # NULL for super-admin

    @property
    def is_admin(self):
        """True if user is any type of admin (superadmin or tenant admin)"""
        return self.role in ('admin', 'superadmin')

    @property
    def is_manager(self):
        return self.role == 'manager'

    @property
    def is_super_admin(self):
        """Super-admin has role='superadmin'"""
        return self.role == 'superadmin'

    @property
    def is_tenant_admin(self):
        """Tenant admin has role='admin' (and tenant_id is NOT NULL)"""
    @property
    def is_super_admin_old(self):
        """Legacy: Super-admin had role='admin' and tenant_id=NULL (deprecated)"""
        return self.role == 'admin' and self.tenant_id is None

    libraries = db.relationship('Library', secondary='user_libraries', lazy='subquery',
                                back_populates='users')
    favorites = db.relationship('Book', secondary=favorites, lazy='subquery',
                                backref=db.backref('favorited_by', lazy=True))
    # Add relation to notifications
    received_notifications = db.relationship(
        'Notification', foreign_keys='Notification.recipient_id', back_populates='recipient', lazy=True, cascade='all, delete-orphan')
    sent_notifications = db.relationship(
        'Notification', foreign_keys='Notification.sender_id', back_populates='sender', lazy=True)

    comments = db.relationship('Comment', back_populates='user', lazy=True, cascade='all, delete-orphan')

    @staticmethod
    def for_tenant(tenant_id):
        return User.query.filter_by(tenant_id=tenant_id)

    def __str__(self):
        return self.username

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=False)
    reservation_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    issue_date = db.Column(db.DateTime)
    return_date = db.Column(db.DateTime)

    status = db.Column(db.String(50), default='pending', nullable=False)

    book = db.relationship('Book', backref='loans')
    user = db.relationship('User', back_populates='loans')

    # Add relation to the notifications
    notifications = db.relationship(
        'Notification', back_populates='loan', lazy=True, cascade='all, delete-orphan')

    @staticmethod
    def for_tenant(tenant_id):
        return Loan.query.filter_by(tenant_id=tenant_id)

    def __str__(self):
        return f"Loan {self.id}: {self.book.title} to {self.user.username} - Status: {self.status}"


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    message = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    type = db.Column(db.String(100), nullable=False)
    loan_id = db.Column(db.Integer, db.ForeignKey('loan.id'), nullable=True)
    contact_message_id = db.Column(db.Integer, db.ForeignKey('contact_message.id'), nullable=True)

    recipient = db.relationship(
        'User', foreign_keys=[recipient_id], back_populates='received_notifications')
    sender = db.relationship('User', foreign_keys=[
                             sender_id], back_populates='sent_notifications')
    loan = db.relationship('Loan', back_populates='notifications')
    contact_message = db.relationship('ContactMessage')

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.message[:50]}..."


class LibraryAccessRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    library_id = db.Column(db.Integer, db.ForeignKey('library.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # 'pending', 'approved', 'rejected'
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    user = db.relationship('User', backref='access_requests')
    library = db.relationship('Library', backref='access_requests')

    @staticmethod
    def for_tenant(tenant_id):
        return LibraryAccessRequest.query.join(Library).filter(Library.tenant_id == tenant_id)

    def __str__(self):
        return f"Request from {self.user.username} for {self.library.name} - Status: {self.status}"


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=True)

    user = db.relationship('User', back_populates='comments')
    book = db.relationship('Book', back_populates='comments')

    @staticmethod
    def for_tenant(tenant_id):
        return Comment.query.join(Book).filter(Book.tenant_id == tenant_id)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.book.title} at {self.timestamp}"


class InvitationCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(8), unique=True, nullable=False, index=True)

    # Kto wygenerował
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_by = db.relationship('User', foreign_keys=[created_by_id],
                                 backref='generated_invitations')

    # Do której biblioteki
    library_id = db.Column(db.Integer, db.ForeignKey('library.id'), nullable=False)
    library = db.relationship('Library', backref='invitation_codes')

    # Do którego tenanta
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=False)
    tenant = db.relationship('Tenant', backref='invitation_codes')

    # Śledzenie użycia
    used_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    used_by = db.relationship('User', foreign_keys=[used_by_id],
                              backref='registered_via_invitation')

    # Czasowe
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    used_at = db.Column(db.DateTime, nullable=True)

    def is_valid(self):
        """Sprawdza czy kod jest jeszcze ważny i nieużyty"""
        return (self.used_by_id is None and
                self.expires_at > datetime.datetime.utcnow())

    def mark_as_used(self, user_id):
        """Oznacz kod jako użyty"""
        self.used_by_id = user_id
        self.used_at = datetime.datetime.utcnow()
        db.session.commit()

    def __str__(self):
        return f"Code {self.code} for {self.library.name} - {'Active' if self.is_valid() else 'Inactive'}"


# Model wiadomości kontaktowej
class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship('User', foreign_keys=[user_id], backref='contact_messages')
    library_id = db.Column(db.Integer, db.ForeignKey('library.id'), nullable=False)
    library = db.relationship('Library', backref='contact_messages')
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Odpowiedź
    reply_message = db.Column(db.Text, nullable=True)
    reply_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    reply_by = db.relationship('User', foreign_keys=[reply_by_id])
    replied_at = db.Column(db.DateTime, nullable=True)

    # Status
    read_by_admin = db.Column(db.Boolean, default=False)
    is_resolved = db.Column(db.Boolean, default=False)

    @staticmethod
    def for_tenant(tenant_id):
        return ContactMessage.query.join(Library).filter(Library.tenant_id == tenant_id)

    def __str__(self):
        return f"ContactMessage from {self.user_id} in library {self.library_id} at {self.created_at}"


class AdminSuperAdminConversation(db.Model):
    """Conversation between tenant admin and super-admin"""
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=False, index=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    subject = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)

    tenant = db.relationship('Tenant', backref='admin_conversations')
    admin = db.relationship('User', backref='admin_super_admin_conversations')
    messages = db.relationship('AdminSuperAdminMessage', backref='conversation',
                               cascade='all, delete-orphan', lazy=True)

    def __str__(self):
        return f"Conversation: {self.subject} (Tenant: {self.tenant.name})"

    @property
    def unread_count(self):
        """Count unread messages for super-admin"""
        return AdminSuperAdminMessage.query.filter_by(
            conversation_id=self.id,
            read=False
        ).count()


class AdminSuperAdminMessage(db.Model):
    """Individual message in conversation between admin and super-admin"""
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey(
        'admin_super_admin_conversation.id'), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)
    read = db.Column(db.Boolean, default=False)

    sender = db.relationship('User', foreign_keys=[sender_id])

    def __str__(self):
        return f"Message from {self.sender.username}: {self.message[:50]}..."


# Poprawka logiki logowania multi-tenant:
# W pliku routes/auth.py:
#
# 1. Pobierz tenant_name z formularza logowania (np. <input name="tenant"> lub select)
# 2. Znajdź tenant po nazwie
# 3. Szukaj użytkownika po loginie/emailu i tenant_id
# 4. Sprawdź hasło i loguj użytkownika
#
# Przykład (do wstawienia w login_post):
#
# tenant_name = request.form.get('tenant')
# tenant = Tenant.query.filter_by(name=tenant_name).first()
# if not tenant:
#     flash('Nieprawidłowy tenant', 'danger')
#     return redirect(url_for('auth.login'))
# if '@' in username:
#     user = User.query.filter_by(email=username, tenant_id=tenant.id).first()
# else:
#     user = User.query.filter_by(username=username, tenant_id=tenant.id).first()
#
# ...dalej sprawdzaj hasło i loguj użytkownika...
#
# UWAGA: Dodaj pole wyboru tenant w formularzu logowania (np. select z listą tenantów)
#
# Ten kod nie wymaga zmian w models.py, tylko w routes/auth.py oraz w szablonie logowania.
