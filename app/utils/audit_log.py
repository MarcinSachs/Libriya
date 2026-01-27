"""
Audit logging system for tracking sensitive operations in the application.
Logs are stored in a rotating file to track user actions and system events.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from flask import request
from flask_login import current_user


def get_audit_logger():
    """Initialize and return audit logger with rotating file handler."""
    logger = logging.getLogger('audit')

    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.INFO)

    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'logs'
    )
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # Create rotating file handler (max 10MB per file, keep 10 files)
    handler = RotatingFileHandler(
        os.path.join(logs_dir, 'audit.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10
    )

    # Create formatter with detailed information
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def log_audit_event(event_type: str, description: str, target_id: int = None,
                    additional_info: dict = None, severity: str = 'INFO'):
    """
    Log an audit event.

    Args:
        event_type (str): Type of event (e.g., 'USER_CREATED', 'PASSWORD_CHANGED')
        description (str): Human-readable description of the event
        target_id (int): ID of the affected resource
        additional_info (dict): Additional context information
        severity (str): Log severity level ('INFO', 'WARNING', 'ERROR')
    """
    logger = get_audit_logger()

    # Build log message
    user_info = (
        f"User: {current_user.username} (ID: {current_user.id})"
        if current_user.is_authenticated
        else "User: Anonymous"
    )
    ip_address = request.remote_addr if request else "N/A"

    log_message = f"{event_type} | {user_info} | IP: {ip_address} | {description}"

    if target_id:
        log_message += f" | Target ID: {target_id}"

    if additional_info:
        log_message += f" | Details: {str(additional_info)}"

    # Log at appropriate level
    if severity == 'WARNING':
        logger.warning(log_message)
    elif severity == 'ERROR':
        logger.error(log_message)
    else:
        logger.info(log_message)


# Specific audit logging functions for common operations
def log_user_created(user_id: int, username: str, email: str):
    """Log user creation."""
    log_audit_event(
        'USER_CREATED',
        f"New user created: {username}",
        user_id,
        {'username': username, 'email': email}
    )


def log_user_deleted(user_id: int, username: str):
    """Log user deletion."""
    log_audit_event(
        'USER_DELETED',
        f"User deleted: {username}",
        user_id,
        {'username': username},
        severity='WARNING'
    )


def log_user_role_changed(user_id: int, username: str,
                          old_role: str, new_role: str):
    """Log role modification."""
    log_audit_event(
        'ROLE_MODIFIED',
        f"User {username} role changed: {old_role} -> {new_role}",
        user_id,
        {'old_role': old_role, 'new_role': new_role},
        severity='WARNING'
    )


def log_password_changed(user_id: int, username: str):
    """Log password change."""
    log_audit_event(
        'PASSWORD_CHANGED',
        f"Password changed for user: {username}",
        user_id,
        {'username': username}
    )


def log_failed_login(username: str):
    """Log failed login attempt."""
    ip_address = request.remote_addr if request else "N/A"
    logger = get_audit_logger()
    logger.warning(
        f"FAILED_LOGIN | Username: {username} | IP: {ip_address}"
    )


def log_book_deleted(book_id: int, title: str):
    """Log book deletion."""
    log_audit_event(
        'BOOK_DELETED',
        f"Book deleted: {title}",
        book_id,
        {'title': title},
        severity='WARNING'
    )


def log_library_operation(operation: str, library_id: int,
                          library_name: str, description: str):
    """Log library-related operations."""
    log_audit_event(
        f"LIBRARY_{operation.upper()}",
        f"Library operation: {description}",
        library_id,
        {'library_name': library_name}
    )
