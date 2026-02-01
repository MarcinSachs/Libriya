"""Background task scheduler for periodic cleanup tasks"""
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import logging

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


def shutdown_scheduler():
    """Shutdown the scheduler gracefully"""
    global scheduler

    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped")
