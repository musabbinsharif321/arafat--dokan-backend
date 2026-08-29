web: python manage.py migrate && python seed_data.py && gunicorn dokan_backend.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 4 --timeout 120 --access-logfile - --error-logfile -
