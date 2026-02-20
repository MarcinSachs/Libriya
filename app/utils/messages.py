"""
Standardized flash messages for the application.
All messages use consistent formatting and categorization.
"""

from flask_babel import lazy_gettext as _

# Success messages
SUCCESS_CREATED = _("%(item)s has been created successfully.")
SUCCESS_UPDATED = _("%(item)s has been updated successfully.")
SUCCESS_DELETED = _("%(item)s has been deleted successfully.")
SUCCESS_ACTION = _("Action completed successfully.")
SUCCESS_SAVED = _("Changes have been saved.")

# Error messages
ERROR_NOT_FOUND = _("%(item)s not found.")
ERROR_PERMISSION_DENIED = _("You do not have permission to perform this action.")
ERROR_INVALID_INPUT = _("Invalid input provided.")
ERROR_DUPLICATE = _("%(item)s already exists.")
ERROR_REQUIRED_FIELD = _("%(field)s is required.")
ERROR_INVALID_FORMAT = _("Invalid %(field)s format.")

# Warning messages
WARNING_CONFIRM = _("This action cannot be undone. Please confirm.")
WARNING_UNSAVED_CHANGES = _("You have unsaved changes.")

# Info messages
INFO_NO_RESULTS = _("No results found.")
INFO_LANGUAGE_CHANGED_PL = "Język zmieniony na polski."
INFO_LANGUAGE_CHANGED_EN = "Language changed to English."

# Specific messages
BOOK_ADDED = _("Book %(title)s has been added successfully.")
BOOK_UPDATED = _("Book %(title)s has been updated successfully.")
BOOK_DELETED = _("Book %(title)s has been deleted successfully.")
BOOK_RESERVED = _("Book has been reserved successfully. An admin will approve it shortly.")
BOOK_ALREADY_RESERVED = _("This book is already reserved by another user.")

USER_ADDED = _("User %(username)s has been created successfully.")
USER_UPDATED = _("User %(username)s has been updated successfully.")
USER_DELETED = _("User %(username)s has been deleted successfully.")
USER_CANNOT_DELETE_SELF = _("You cannot delete your own account.")
USER_CANNOT_DELETE_ADMIN = _("You cannot delete an administrator.")
USER_NO_PERMISSION_EDIT = _("You do not have permission to edit this user.")
USER_NOT_IN_LIBRARY = _("You can only manage users from your libraries.")

LIBRARY_ADDED = _("Library has been created successfully.")
LIBRARY_UPDATED = _("Library has been updated successfully.")
LIBRARY_DELETED = _("Library has been deleted successfully.")

LOAN_CREATED = _("Loan has been created successfully.")
LOAN_UPDATED = _("Loan has been updated successfully.")
LOAN_COMPLETED = _("Loan has been marked as completed.")

INVITATION_CODE_GENERATED = _("Invitation code has been generated: %(code)s")
INVITATION_CODE_DEACTIVATED = _("Invitation code has been deactivated.")

NOTIFICATION_MARKED_READ = _("Notification has been marked as read.")
NOTIFICATION_ALL_MARKED_READ = _("All notifications have been marked as read.")

# Auth messages
AUTH_LOGIN_SUCCESS = _("Login successful!")
AUTH_INVALID_CREDENTIALS = _("Invalid username or password. Please try again.")
AUTH_LOGOUT_SUCCESS = _("You have been logged out.")
AUTH_REGISTRATION_SUCCESS = _("Registration successful! You can now log in.")

# Additional messages
COMMENT_ADDED = _("Your comment has been added!")
COMMENT_UPDATED = _("Your comment has been updated!")
BOOK_ALREADY_IN_FAVORITES = _("Book is already in favorites.")
BOOK_ADDED_TO_FAVORITES = _("Book added to favorites.")
BOOK_REMOVED_FROM_FAVORITES = _("Book removed from favorites.")
BOOK_NOT_IN_FAVORITES = _("Book is not in favorites.")
BOOK_CANNOT_DELETE_NOT_AVAILABLE = _(
    'Cannot delete "%(title)s" because it is currently "%(status)s". Consider marking it as inactive instead.')
BOOKS_ONLY_EDIT_OWN_LIBRARIES = _("You can only edit books within your libraries.")
COVER_IMAGE_ERROR = _("Could not download cover image: %(error)s")

# User management messages
USERS_NO_LIBRARY_MANAGED = _("You do not manage any library. Cannot add user.")
USERS_NO_PERMISSION_EDIT_ROLE = _("You do not have permission to edit this user's role.")
USERS_ONLY_EDIT_OWN_LIBRARIES = _("You can only edit users within your libraries.")
USERS_CANNOT_REVOKE_LAST_ADMIN = _("You cannot revoke the last administrator's role.")
USERS_NO_PERMISSION_CREATE_ADMIN = _("You do not have permission to create administrators.")
USERS_CANNOT_DELETE_SELF = _("You cannot delete your own account.")
USERS_CANNOT_DELETE_ADMIN = _("You cannot delete an administrator.")
USERS_ONLY_DELETE_OWN_LIBRARIES = _("You can only delete users from your libraries.")
USERS_SETTINGS_NO_USER = _("No user found to edit settings.")
USERS_SETTINGS_UPDATED = _("Your settings have been updated.")

# Loan management messages
LOAN_FILTER_INVALID_USER = _("Invalid user ID provided for filtering.")
LOANS_BOOK_RESERVED = _("Book has been reserved successfully! An admin will approve it shortly.")
LOANS_BOOK_ALREADY_RESERVED = _("This book is already reserved by another user.")
LOANS_BOOK_ON_LOAN = _("This book is currently on loan.")
LOANS_BORROWED_SUCCESS = _("Book borrowed successfully!")
LOANS_BOOK_NOT_AVAILABLE = _("This book is not available for direct loan.")
LOANS_RETURNED_SUCCESS = _("Book returned successfully!")
LOANS_BOOK_NOT_ON_LOAN = _("This book is not currently on loan or is already returned.")
LOANS_APPROVED = _('Loan for "%(title)s" to %(username)s has been approved!')
LOANS_CANNOT_APPROVE_STATUS = _(
    'Cannot approve loan: Book status is not "reserved". It might have been cancelled or loaned differently.')
LOANS_NOT_PENDING = _('Loan is not in "pending" status and cannot be approved.')
LOANS_RESERVATION_CANCELLED = _('Reservation for "%(title)s" by %(username)s has been cancelled.')
LOANS_CANCEL_NOT_PENDING = _('Cannot cancel loan: It is not in "pending" status.')
LOANS_ADMIN_RETURNED = _('Book "%(title)s" has been returned.')
LOANS_NOT_ACTIVE = _('This loan is not active or has already been returned.')
LOANS_ADDED_SUCCESS = _("Loan added successfully!")
LOANS_BOOK_UNAVAILABLE = _("This book is currently on loan or reserved.")
LOANS_INVALID_BOOK_USER = _("Invalid book or user.")
LOANS_CAN_ONLY_CANCEL_OWN = _("You can only cancel your own reservations.")
LOANS_USER_RESERVATION_CANCELLED = _("Your reservation for %(title)s has been cancelled.")
LOANS_CANNOT_CANCEL_NOT_PENDING = _("This reservation cannot be cancelled as it is not in 'pending' status.")

# Library management messages
LIBRARIES_CANNOT_DELETE_WITH_BOOKS = _("Cannot delete a library that has books associated with it.")
LIBRARIES_CANNOT_DELETE_WITH_USERS = _("Cannot delete a library that has users assigned to it.")

# Invitation management messages
INVITATIONS_SELECT_LIBRARY = _("Please select a library")
INVITATIONS_ONLY_OWN_LIBRARIES = _("You can only generate codes for your libraries")
INVITATIONS_CODE_GENERATED = _("Invitation code generated: %(code)s")
INVITATIONS_EMAIL_SENT = _("Invitation sent to %(email)s")
INVITATIONS_EMAIL_COLUMN = _("Email sent")
INVITATIONS_NO_RECIPIENT = _("No recipient email specified for this code")
INVITATIONS_EMAIL_SEND_ERROR = _("Failed to send invitation email.")
INVITATIONS_NO_PERMISSION_DEACTIVATE = _("You do not have permission to deactivate this code")
INVITATIONS_CANNOT_DEACTIVATE_USED = _("Cannot deactivate an already-used code")
INVITATIONS_CODE_DEACTIVATED = _("Invitation code deactivated")

# Error-specific messages
ERROR_UNSUPPORTED_LANGUAGE = _("Unsupported language.")
