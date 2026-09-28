#!/bin/sh
set -e

# Use PORT from environment or default to 8000
PORT="${PORT:-8000}"
echo "Starting Dokan ERP Backend on port $PORT..."

# 1. Collect static files
python manage.py collectstatic --noinput

# 2. Run database migrations
python manage.py migrate
# 3. Start automated Google Drive backup scheduler in background (if configured)
if [ "$ENABLE_AUTO_BACKUP" = "true" ] || [ -n "$GDRIVE_FOLDER_ID" ]; then
    echo "Starting automated Google Drive backup scheduler in background..."
    python manage.py run_backup_scheduler &
fi
# 4. Start production Gunicorn WSGI server
exec gunicorn dokan_backend.wsgi:application \
    --bind "0.0.0.0:$PORT" \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
