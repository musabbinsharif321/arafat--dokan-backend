web: python manage.py collectstatic --noinput && python manage.py migrate && python seed_data.py && gunicorn dokan_backend.wsgi:application --bind 0.0.0.0:$PORT
