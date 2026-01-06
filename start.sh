#!/bin/bash
# Startup script that runs migrations and seeds database before starting the server

set -e  # Exit on error

echo "=== Running migrations ==="
python manage.py migrate --settings=bom_configurator.settings_production

echo "=== Importing CSV data ==="
python manage.py import_csv_data --force --settings=bom_configurator.settings_production || echo "CSV import completed or skipped"

echo "=== Seeding database ==="
python manage.py migrate_and_seed --settings=bom_configurator.settings_production || echo "Seeding completed or skipped"

echo "=== Collecting static files ==="
python manage.py collectstatic --noinput --settings=bom_configurator.settings_production || echo "Static files collected or skipped"

echo "=== Starting server ==="
exec gunicorn --env DJANGO_SETTINGS_MODULE=bom_configurator.settings_production bom_configurator.wsgi:application

