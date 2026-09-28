import os
import time
import logging
from django.core.management.base import BaseCommand
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

logger = logging.getLogger("dokan_backup")

def scheduled_job():
    logger.info("Executing scheduled daily backup...")
    try:
        from api.backup_utils import perform_full_backup_to_gdrive
        res = perform_full_backup_to_gdrive()
        logger.info(f"Scheduled backup outcome: {res}")
    except Exception as e:
        logger.error(f"Scheduled backup encountered error: {e}", exc_info=True)

class Command(BaseCommand):
    help = "Runs the background backup scheduler for Dokan ERP"

    def handle(self, *args, **options):
        tz_str = os.environ.get("BACKUP_TIMEZONE", "Asia/Dhaka")
        backup_time = os.environ.get("BACKUP_TIME_DHAKA", "00:00").strip()
        folder_id = os.environ.get("GDRIVE_FOLDER_ID", "").strip()
        sa_json = os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON", "").strip()
        sa_file = os.environ.get("GDRIVE_SERVICE_ACCOUNT_FILE", "").strip()

        if not folder_id or (not sa_json and not sa_file):
            self.stdout.write(self.style.WARNING(
                "Backup scheduler started, but GDRIVE_FOLDER_ID and/or Service Account credentials "
                "are not configured. The scheduler will idle safely. Configure them in Railway to activate."
            ))
            # Sleep loop to keep process alive without error
            while True:
                time.sleep(3600)

        try:
            hour_str, minute_str = backup_time.split(":")
            hour = int(hour_str)
            minute = int(minute_str)
        except Exception:
            hour, minute = 0, 0

        tz = pytz.timezone(tz_str)
        scheduler = BlockingScheduler(timezone=tz)

        scheduler.add_job(
            scheduled_job,
            trigger=CronTrigger(hour=hour, minute=minute, timezone=tz),
            id="daily_dokan_gdrive_backup",
            name="Daily Dokan Google Drive Backup",
            replace_existing=True,
            misfire_grace_time=3600
        )

        self.stdout.write(self.style.SUCCESS(
            f"=== Dokan Backup Scheduler Started ===\n"
            f"Schedule: Daily at {hour:02d}:{minute:02d} ({tz_str})\n"
            f"Target Google Drive Folder: {folder_id}\n"
            f"Listening for next run..."
        ))

        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            self.stdout.write("Backup scheduler shutting down.")
