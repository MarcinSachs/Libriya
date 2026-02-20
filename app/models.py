from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import datetime
import secrets
import hashlib
from datetime import timedelta


class Tenant(db.Model):
    """Represents a tenant (organization/library system).

    Attributes:
        id (int): Primary key
        name (str): Tenant display name
        subdomain (str): Tenant subdomain used for routing
        premium_bookcover_enabled (bool): Feature flag for bookcover API
        premium_biblioteka_narodowa_enabled (bool): Feature flag for BN integration
        premium_batch_import_enabled (bool): Feature flag for batch import
        created_at (datetime): Creation timestamp
        updated_at (datetime): Last update timestamp
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    subdomain = db.Column(db.String(100), unique=True, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    status = db.Column(db.String(50), default='active', nullable=False)

    # Premium features - tenant-specific
    premium_bookcover_enabled = db.Column(db.Boolean, default=False, nullable=False)
    premium_biblioteka_narodowa_enabled = db.Column(db.Boolean, default=False, nullable=False)
    premium_batch_import_enabled = db.Column(db.Boolean, default=False, nullable=False)

    # Limits (None or -1 means unlimited)
    max_libraries = db.Column(db.Integer, nullable=True, default=1)  # Default: 1 library
    max_books = db.Column(db.Integer, nullable=True, default=10)     # Default: 10 books

    libraries = db.relationship('Library', backref='tenant', lazy=True)
    users = db.relationship('User', backref='tenant', lazy=True)

    def has_unlimited_libraries(self):
        return self.max_libraries is None or self.max_libraries < 0

    def has_unlimited_books(self):
        return self.max_books is None or self.max_books < 0

    def can_add_library(self):
        if self.has_unlimited_libraries():
            return True
        return len(self.libraries) < self.max_libraries

    def can_add_book(self):
        if self.has_unlimited_books():
            return True
        # Sum all books in all libraries for this tenant
        return sum(len(lib.books) for lib in self.libraries) < self.max_books

    def __str__(self):
        return f"{self.name} ({self.subdomain})"

    def get_enabled_premium_features(self):
        """Return list of enabled premium features for this tenant."""
        features = []
        if self.premium_bookcover_enabled:
            features.append('bookcover_api')
        if self.premium_biblioteka_narodowa_enabled:
            features.append('biblioteka_narodowa')
        if self.premium_batch_import_enabled:
            features.append('batch_import')
        return features

    def is_premium_enabled(self, feature_id):
        """Check if a specific premium feature is enabled for this tenant."""
        feature_map = {
            'bookcover_api': 'premium_bookcover_enabled',
            'biblioteka_narodowa': 'premium_biblioteka_narodowa_enabled',
            'batch_import': 'premium_batch_import_enabled',
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
    """Represents a library belonging to a tenant.

    Attributes:
        id (int): Primary key
        name (str): Library name
        tenant_id (int): Foreign key to `Tenant`
        loan_overdue_days (int): Default allowed loan duration in days
    """
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
    """Book entity stored in a library.

    Attributes:
        id (int): Primary key
        library_id (int): FK to `Library`
        tenant_id (int): FK to `Tenant`
        isbn (str): ISBN number if present
        title (str): Book title
        year (int): Publication year
        status (str): Availability status ('available', 'reserved', 'on_loan')
    """
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
    """Author of books.

    Attributes:
        id (int): Primary key
        name (str): Author full name
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    books = db.relationship('Book', secondary=book_authors,
                            lazy='subquery', back_populates='authors')

    def __str__(self):
        return self.name


class Genre(db.Model):
    """Genre/category for books.

    Attributes:
        id (int): Primary key
        name (str): Genre name
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, index=True)
    books = db.relationship('Book', secondary=book_genres,
                            lazy='subquery', back_populates='genres')

    def __str__(self):
        return self.name


class User(UserMixin, db.Model):
    """Application user model.

    Attributes:
        id (int): Primary key
        username (str): Unique login name
        email (str): User email
        role (str): Role identifier ('user','manager','admin','superadmin')
        tenant_id (int|None): FK to `Tenant` (NULL for super-admin)
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True,
                         nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)  # INCREASED from 128 to 255 to accommodate PBKDF2 hashes
    # Email verification status
    is_email_verified = db.Column(db.Boolean, default=False, nullable=False)
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
        return self.role == 'admin' and self.tenant_id is not None

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
    """Represents a loan/reservation of a book by a user.

    Attributes:
        id (int): Primary key
        book_id (int): FK to `Book`
        user_id (int): FK to `User`
        tenant_id (int): FK to `Tenant`
        status (str): Loan status ('pending','issued','returned')
    """
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id', ondelete='CASCADE'), nullable=False)
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
    """In-app notification sent between users.

    Attributes:
        id (int): Primary key
        recipient_id (int): FK to receiving `User`
        sender_id (int|None): FK to sending `User` (may be null)
        message (str): Notification text
        type (str): Notification type identifier
    """
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
    """Request for library access created by a user.

    Attributes:
        id (int): Primary key
        user_id (int): FK to requesting `User`
        library_id (int): FK to `Library`
        status (str): 'pending', 'approved', or 'rejected'
    """
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
    """User comment on a book.

    Attributes:
        id (int): Primary key
        user_id (int): FK to authoring `User`
        book_id (int): FK to `Book`
        text (str): Comment text
        timestamp (datetime): When comment was created
    """
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
    """Invitation code used to register users into a library/tenant.

    Attributes:
        id (int): Primary key
        code (str): Short unique invitation code
        library_id (int): FK to target `Library`
        tenant_id (int): FK to target `Tenant`
        used_by_id (int|None): FK to `User` that used the code
    """
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

    # optional email address the code was sent to (if any)
    recipient_email = db.Column(db.String(200), nullable=True)
    # timestamp when invitation was emailed (optional)
    email_sent_at = db.Column(db.DateTime, nullable=True)

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
        base = f"Code {self.code} for {self.library.name} - {'Active' if self.is_valid() else 'Inactive'}"
        if self.recipient_email:
            base += f" (sent to {self.recipient_email})"
        return base


# Shared links for public book lists
class SharedLink(db.Model):
    """Public share links for a library's books.

    Attributes:
        id (int): primary key
        token (str): unguessable link token
        library_id (int): FK to Library being shared
        created_by_id (int): FK to User who generated link
        created_at (datetime): when link was created
        expires_at (datetime|None): optional expiry date/time
        active (bool): whether link is still valid
    """
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    library_id = db.Column(db.Integer, db.ForeignKey('library.id'), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    active = db.Column(db.Boolean, default=True, nullable=False)

    library = db.relationship('Library', backref='shared_links')
    created_by = db.relationship('User', backref='generated_shares')

    def is_valid(self):
        if not self.active:
            return False
        if self.expires_at and self.expires_at < datetime.datetime.utcnow():
            return False
        return True

    def __str__(self):
        status = 'active' if self.is_valid() else 'inactive'
        return f"Share {self.token} for {self.library.name} ({status})"


# Model wiadomości kontaktowej
class ContactMessage(db.Model):
    """Message submitted via contact form for a library.

    Attributes:
        id (int): Primary key
        user_id (int|None): FK to `User` if sender is logged in
        library_id (int): FK to `Library`
        subject (str): Message subject
        message (str): Body text
        created_at (datetime): Creation timestamp
    """
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


class AuditLogFile(db.Model):
    """Metadata for file-based audit logs.

    One record per log file. Super-admin UI will list these entries so files can
    be previewed, archived or purged according to retention policy.
    """
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=True, index=True)
    filename = db.Column(db.String(500), nullable=False, unique=True, index=True)
    start_ts = db.Column(db.DateTime, nullable=True)
    end_ts = db.Column(db.DateTime, nullable=True)
    size = db.Column(db.Integer, nullable=True)
    archived = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)

    tenant = db.relationship('Tenant', backref='audit_log_files')

    def __str__(self):
        return f"AuditLogFile: {self.filename} (tenant={self.tenant_id})"


class PasswordResetToken(db.Model):
    """One-time password reset tokens (DB-backed).

    Stores only the sha256 hash of the token so the raw token is only returned
    once to be sent by email. Tokens are single-use and expire after a period.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    token_hash = db.Column(db.String(128), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)

    user = db.relationship('User', backref='password_reset_tokens')

    @classmethod
    def generate_token(cls, user_id, expires_in=3600):
        """Generate a token for user_id, store hash and return raw token."""
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        now = datetime.datetime.utcnow()
        expires_at = now + timedelta(seconds=expires_in)
        entry = cls(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        db.session.add(entry)
        db.session.commit()
        return token

    @classmethod
    def verify_token(cls, token):
        """Verify raw token and return DB entry if valid and not used/expired."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        entry = cls.query.filter_by(token_hash=token_hash).first()
        if not entry:
            return None
        if entry.used:
            return None
        if entry.expires_at < datetime.datetime.utcnow():
            return None
        return entry

    def mark_used(self):
        self.used = True
        db.session.commit()

    def __str__(self):
        return f"PasswordResetToken(user_id={self.user_id}, used={self.used}, expires_at={self.expires_at})"


class EmailVerificationToken(db.Model):
    """DB-backed email verification tokens (single-use).

    Pattern mirrors PasswordResetToken: store only the sha256 hash, expire and single-use.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    token_hash = db.Column(db.String(128), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)

    user = db.relationship('User', backref='email_verification_tokens')

    @classmethod
    def generate_token(cls, user_id, expires_in=86400):
        """Generate token for email verification (default 24h expiry)."""
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        now = datetime.datetime.utcnow()
        expires_at = now + timedelta(seconds=expires_in)
        entry = cls(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        db.session.add(entry)
        db.session.commit()
        return token

    @classmethod
    def verify_token(cls, token):
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        entry = cls.query.filter_by(token_hash=token_hash).first()
        if not entry:
            return None
        if entry.used:
            return None
        if entry.expires_at < datetime.datetime.utcnow():
            return None
        return entry

    def mark_used(self):
        self.used = True
        db.session.commit()

    def __str__(self):
        return f"EmailVerificationToken(user_id={self.user_id}, used={self.used}, expires_at={self.expires_at})"


class AuditLog(db.Model):
    """Row-level audit log for critical application events.

    - Stored as DB rows for easy querying and short-term retention.
    - Long-term/permanent audit files are handled by AuditLogFile (JSON-lines).
    """
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=True, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    actor_role = db.Column(db.String(50), nullable=True)
    ip = db.Column(db.String(45), nullable=True)

    action = db.Column(db.String(120), nullable=False, index=True)
    object_type = db.Column(db.String(100), nullable=True, index=True)
    object_id = db.Column(db.String(100), nullable=True, index=True)
    details = db.Column(db.Text, nullable=True)  # JSON string (small)
    success = db.Column(db.Boolean, default=True, nullable=False)

    actor = db.relationship('User', foreign_keys=[actor_id])
    tenant = db.relationship('Tenant', backref='audit_logs')

    def __repr__(self):
        return f"<AuditLog {self.id} action={self.action} actor={self.actor_id} tenant={self.tenant_id} ts={self.timestamp}>"
