web: python manage.py migrate && python seed_data.py && python -m gunicorn dokan_backend.wsgi --bind 0.0.0.0:$PORT --log-file -
