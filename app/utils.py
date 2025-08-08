import os
import datetime as dt
import logging
import traceback
from apscheduler.schedulers.background import BackgroundScheduler
from .extensions import db
from .models import EchoCounts


def schedule_echo_deletion(app):
    """Schedule deletion of echo records"""
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=lambda: delete_expired_echo_entries(
        app), trigger="interval", days=1, misfire_grace_time=None)
    scheduler.start()


def delete_expired_echo_entries(app):
    """Delete echo counts older than 30 days"""
    logging.info("Deleting old database entries...")

    try:
        max_days = os.getenv("MAX_DAYS_STORE_ECHOES", 30)

        # Calculate the cutoff date
        cutoff_date = dt.datetime.now(
            dt.timezone.utc) - dt.timedelta(days=max_days)

        with app.app_context():
            # Filter and delete old log entries
            old_entries = EchoCounts.query.filter(
                EchoCounts.timestamp < cutoff_date).all()

            if len(old_entries) == 0:
                logging.info("No old database entries to delete!")
                return

            for entry in old_entries:
                logging.info(
                    f"Deleting old echo counts for '{entry.site_name}' on {entry.timestamp}")
                db.session.delete(entry)

            logging.info(
                f"Successfully deleted {len(old_entries)} old database entries.")

            db.session.commit()
    except Exception as e:
        logging.error(
            f"Failed to delete old database entries due to error:\n{traceback.format_exc()}")
