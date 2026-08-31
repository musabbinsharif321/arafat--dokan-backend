#!/bin/sh
set -e

# Use PORT from environment or default to 8000
PORT="${PORT:-8000}"
echo "Starting Dokan ERP Backend on port $PORT..."

# 1. Collect static files
python manage.py collectstatic --noinput

# 2. Run database migrations
python manage.py migrate



# 4. Start production Gunicorn WSGI server
exec gunicorn dokan_backend.wsgi:application \
    --bind "0.0.0.0:$PORT" \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
