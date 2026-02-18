# Models Reference

This file documents the main ORM models used by the Libriya application. It is generated from `app/models.py` docstrings and provides quick reference for developers.

- Tenant
- Library
- Book
- Author
- Genre
- Location
- User
- Loan
- Notification
- LibraryAccessRequest
- Comment
- InvitationCode
- ContactMessage
- AdminSuperAdminConversation

---

## Tenant
Represents a tenant (organization/library system).

Attributes:
- `id` (int): Primary key
- `name` (str): Tenant display name
- `subdomain` (str): Tenant subdomain used for routing
- `created_at` (datetime): Creation timestamp
- `updated_at` (datetime): Last update timestamp
- `premium_bookcover_enabled` (bool): Feature flag for bookcover API
- `premium_biblioteka_narodowa_enabled` (bool): Feature flag for BN integration

Utility methods:
- `get_enabled_premium_features()` -> list of enabled feature ids
- `is_premium_enabled(feature_id)` -> bool

---

## Library
Represents a library belonging to a tenant.

Attributes:
- `id` (int): Primary key
- `name` (str): Library name
- `tenant_id` (int): Foreign key to `Tenant`
- `loan_overdue_days` (int): Default loan duration in days

---

## Book
Book entity stored in a library.

Attributes:
- `id` (int): Primary key
- `library_id` (int): FK to `Library`
- `tenant_id` (int): FK to `Tenant`
- `isbn` (str): ISBN number if present
- `title` (str): Book title
- `year` (int): Publication year
- `status` (str): Availability status (`available`, `reserved`, `on_loan`)
- relationships: `authors`, `genres`, `library`, `location`, `comments`

---

## Author
Author of books.

Attributes:
- `id` (int): Primary key
- `name` (str): Author full name

---

## Genre
Genre/category for books.

Attributes:
- `id` (int): Primary key
- `name` (str): Genre name

---

## Location
Book location information (shelf, section, room, etc.)

Attributes:
- `id` (int): Primary key
- `book_id` (int): FK to `Book` (unique)
- `shelf`, `section`, `room`, `notes`

---

## User
Application user model.

Attributes:
- `id` (int): Primary key
- `username` (str): Unique login name
- `email` (str): User email
- `password_hash` (str)
- `role` (str): Role identifier (`user`, `manager`, `admin`, `superadmin`)
- `tenant_id` (int|None): FK to `Tenant` (NULL for super-admin)
- `is_email_verified` (bool)

Helpers:
- `set_password(password)` / `check_password(password)`
- role properties: `is_admin`, `is_manager`, `is_super_admin`, `is_tenant_admin`

---

## Loan
Represents a loan/reservation of a book by a user.

Attributes:
- `id` (int): Primary key
- `book_id`, `user_id`, `tenant_id`
- `reservation_date`, `issue_date`, `return_date`
- `status` (str)

---

## Notification
In-app notification sent between users.

Attributes:
- `id` (int): Primary key
- `recipient_id` (int): FK to receiving `User`
- `sender_id` (int|None): FK to sending `User` (may be null)
- `message` (str)
- `type` (str)
- `timestamp`

---

## LibraryAccessRequest
Request for library access created by a user.

Attributes:
- `id` (int): Primary key
- `user_id` (int): FK to requesting `User`
- `library_id` (int): FK to `Library`
- `status` (str): `pending`, `approved`, or `rejected`

---

## Comment
User comment on a book.

Attributes:
- `id` (int): Primary key
- `user_id` (int): FK to authoring `User`
- `book_id` (int): FK to `Book`
- `text` (str): Comment text
- `timestamp` (datetime)

---

## InvitationCode
Invitation code used to register users into a library/tenant.

Attributes:
- `id` (int): Primary key
- `code` (str): Short unique invitation code
- `library_id` (int): FK to `Library`
- `tenant_id` (int): FK to `Tenant`
- `used_by_id` (int|None): FK to `User` that used the code
- `expires_at`, `used_at`

---

## ContactMessage
Message submitted via contact form for a library.

Attributes:
- `id` (int): Primary key
- `user_id` (int|None): FK to `User` if sender is logged in
- `library_id` (int): FK to `Library`
- `subject`, `message`, `created_at`, `updated_at`

---

## AdminSuperAdminConversation
Conversation between tenant admin and super-admin.

Attributes:
- `id` (int): Primary key
- `tenant_id`, `admin_id`, `subject`, `created_at`

---

*This document was generated from model docstrings. For more details see `app/models.py`.*
