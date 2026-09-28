from django.core.management.base import BaseCommand
from api.backup_utils import perform_full_backup_to_gdrive

class Command(BaseCommand):
    help = "Creates a full database backup and uploads it to Google Drive."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Initiating database backup to Google Drive..."))
        result = perform_full_backup_to_gdrive()
        if result.get("status") == "success":
            self.stdout.write(self.style.SUCCESS(
                f"Successfully backed up database! File: {result.get('file_name')} (Drive ID: {result.get('gdrive_id')})"
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f"Backup failed: {result.get('error')}"
            ))
            exit(1)
