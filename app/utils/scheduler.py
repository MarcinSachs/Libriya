"""Background task scheduler for periodic cleanup tasks"""
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import logging
import os

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None


def init_scheduler(app):
    """Initialize APScheduler with Flask app context"""
    global scheduler

    if scheduler is not None:
        return  # Already initialized

    scheduler = BackgroundScheduler()
    scheduler.configure(
        jobstores={'default': {'type': 'memory'}},
        job_defaults={'coalesce': True, 'max_instances': 1}
    )

    # Add cleanup job - runs every day at 2:00 AM
    scheduler.add_job(
        cleanup_old_notifications,
        'cron',
        hour=2,
        minute=0,
        args=[app],
        id='cleanup_notifications',
        name='Cleanup old notifications',
        replace_existing=True
    )

    # Add audit logs retention job - runs every day at 3:00 AM
    scheduler.add_job(
        cleanup_old_audit_logs,
        'cron',
        hour=3,
        minute=0,
        args=[app],
        id='cleanup_audit_logs',
        name='Cleanup old audit log files',
        replace_existing=True
    )

    if not scheduler.running:
        scheduler.start()
        logger.info("Background scheduler started")


def cleanup_old_notifications(app):
    """Delete old read notifications (older than 30 days)"""
    with app.app_context():
        from app import db
        from app.models import Notification

        try:
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            deleted_count = Notification.query.filter(
                Notification.is_read == True,
                Notification.timestamp < cutoff_date
            ).delete()

            db.session.commit()
            logger.info(f"Cleanup complete: Deleted {deleted_count} old notifications")
        except Exception as e:
            logger.error(f"Error during notification cleanup: {e}")
            db.session.rollback()


def cleanup_old_audit_logs(app):
    """Remove audit log files older than retention days and their metadata rows."""
    with app.app_context():
        try:
            from app.models import AuditLogFile
            from app import db
            retention_days = app.config.get('AUDIT_RETENTION_DAYS', 30)
            cutoff = datetime.utcnow() - timedelta(days=retention_days)

            logs_root = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')

            # Delete files on disk older than cutoff and remove metadata
            deleted_files = 0
            for alf in AuditLogFile.query.filter(AuditLogFile.created_at < cutoff).all():
                try:
                    filepath = os.path.abspath(alf.filename)
                    if filepath.startswith(os.path.abspath(logs_root)) and os.path.exists(filepath):
                        os.remove(filepath)
                    db.session.delete(alf)
                    deleted_files += 1
                except Exception as e:
                    logger.error(f"Failed to remove audit file {alf.filename}: {e}")
            db.session.commit()
            logger.info(f"Audit log retention: Removed {deleted_files} files older than {retention_days} days")
        except Exception as e:
            logger.error(f"Error during audit log retention: {e}")
            db.session.rollback()


def shutdown_scheduler():
    """Shutdown the scheduler gracefully"""
    global scheduler

    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped")
