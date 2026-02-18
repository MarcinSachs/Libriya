"""
Audit logging system for tracking sensitive operations in the application.
Now writes JSON-lines files per-tenant per-day and records metadata in AuditLogFile model.
"""

import logging
import os
import json
from logging.handlers import TimedRotatingFileHandler
from flask import request, has_request_context
from flask_login import current_user
from pythonjsonlogger import jsonlogger
from datetime import datetime
from app import db
from app.models import AuditLogFile


LOGS_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')


def ensure_logs_dir():
    if not os.path.exists(LOGS_ROOT):
        os.makedirs(LOGS_ROOT, exist_ok=True)


def _build_log_record(action: str, description: str, subject=None, additional_info: dict = None, tenant_id=None):
    record = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'action': action,
        'description': description,
        'tenant_id': tenant_id,
        'actor': None,
        'subject_type': None,
        'subject_id': None,
        'ip': None,
        'details': None,
    }

    if has_request_context():
        record['ip'] = request.remote_addr

    if current_user and getattr(current_user, 'is_authenticated', False):
        record['actor'] = {'id': current_user.id, 'username': current_user.username}
        if record['tenant_id'] is None:
            record['tenant_id'] = getattr(current_user, 'tenant_id', None)

    if subject is not None:
        record['subject_type'] = subject.__class__.__name__ if hasattr(subject, '__class__') else str(type(subject))
        record['subject_id'] = getattr(subject, 'id', None)

    if additional_info:
        # mask potential sensitive keys
        masked = {}
        for k, v in additional_info.items():
            if k.lower() in ('password', 'token', 'secret'):
                masked[k] = '***'
            else:
                masked[k] = v
        record['details'] = masked

    return record


def _log_to_file(record: dict):
    # Determine tenant-specific path
    tenant_part = f"tenant_{record['tenant_id']}" if record.get('tenant_id') else 'global'
    date_part = datetime.utcnow().strftime('%Y-%m-%d')
    tenant_dir = os.path.join(LOGS_ROOT, tenant_part)
    os.makedirs(tenant_dir, exist_ok=True)

    filename = os.path.join(tenant_dir, f"audit_{date_part}.log")

    # Write JSON line directly (append)
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Update or create AuditLogFile metadata
    try:
        alf = AuditLogFile.query.filter_by(filename=filename).first()
        stat = os.stat(filename)
        if not alf:
            alf = AuditLogFile(filename=filename, tenant_id=record.get('tenant_id'), start_ts=None, end_ts=None, size=stat.st_size)
            db.session.add(alf)
        else:
            alf.size = stat.st_size
            alf.tenant_id = record.get('tenant_id')
        alf.end_ts = datetime.utcnow()
        db.session.commit()
    except Exception:
        # Metadata write failures should not break normal flow; log to app logger
        logging.getLogger('audit').exception('Failed to update AuditLogFile metadata')


def log_action(action: str, description: str, subject=None, additional_info: dict = None, tenant_id=None):
    """Generic audit action writer. Writes JSON-line to per-tenant daily file and updates metadata.

    Example: log_action('USER_DELETED', 'Deleted user', subject=user, additional_info={'reason':'spam'})
    """
    ensure_logs_dir()
    rec = _build_log_record(action, description, subject=subject, additional_info=additional_info, tenant_id=tenant_id)
    _log_to_file(rec)


# Backwards-compatible helpers

def log_user_created(user_id: int, username: str, email: str):
    log_action('USER_CREATED', f'New user created: {username}', subject=None, additional_info={'username': username, 'email': email}, tenant_id=None)


def log_user_deleted(user_id: int, username: str):
    log_action('USER_DELETED', f'User deleted: {username}', subject=None, additional_info={'username': username}, tenant_id=None)


def log_user_role_changed(user_id: int, username: str, old_role: str, new_role: str):
    log_action('ROLE_MODIFIED', f'User {username} role changed: {old_role} -> {new_role}', subject=None, additional_info={'old_role': old_role, 'new_role': new_role}, tenant_id=None)


def log_password_changed(user_id: int, username: str):
    log_action('PASSWORD_CHANGED', f'Password changed for user: {username}', subject=None, additional_info={'username': username}, tenant_id=None)


def log_failed_login(username: str):
    log_action('FAILED_LOGIN', f'Failed login attempt for username: {username}', subject=None, additional_info={'username': username}, tenant_id=None)


def log_book_deleted(book_id: int, title: str):
    log_action('BOOK_DELETED', f'Book deleted: {title}', subject=None, additional_info={'title': title}, tenant_id=None)


def log_library_operation(operation: str, library_id: int, library_name: str, description: str):
    log_action(f'LIBRARY_{operation.upper()}', f'Library operation: {description}', subject=None, additional_info={'library_name': library_name}, tenant_id=None)


def log_invitation_code_generated(code: str, library_id: int, library_name: str, days_valid: int):
    log_action('INVITATION_CODE_GENERATED', f'Invitation code generated for {library_name}', subject=None, additional_info={'code': code, 'days_valid': days_valid}, tenant_id=None)


def log_invitation_code_used(code: str, user_id: int, username: str, library_name: str):
    log_action('INVITATION_CODE_USED', f'Invitation code used for registration: {username} -> {library_name}', subject=None, additional_info={'code': code, 'username': username, 'library': library_name}, tenant_id=None)


def log_invitation_code_deactivated(code: str, library_name: str):
    log_action('INVITATION_CODE_DEACTIVATED', f'Invitation code deactivated for {library_name}', subject=None, additional_info={'code': code, 'library': library_name}, tenant_id=None)
