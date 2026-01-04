web: gunicorn --env DJANGO_SETTINGS_MODULE=bom_configurator.settings_production bom_configurator.wsgi:application
release: python manage.py migrate_and_seed --settings=bom_configurator.settings_production && python manage.py collectstatic --noinput --settings=bom_configurator.settings_production
