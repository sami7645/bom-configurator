from django.apps import AppConfig
from django.core.management import call_command
from django.db.models.signals import post_migrate


class ConfiguratorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "configurator"

    def ready(self):
        """Run seeding commands after migrations"""
        post_migrate.connect(self.run_seeding, sender=self)

    def run_seeding(self, sender, **kwargs):
        """Run all seeding commands after migrations"""
        # Only run if this is the configurator app
        if sender.name == 'configurator':
            try:
                # Check if data already exists to avoid re-seeding unnecessarily
                from configurator.models import Schacht
                from django.db import connection
                
                # Check if table exists and is empty
                with connection.cursor() as cursor:
                    try:
                        cursor.execute("SELECT COUNT(*) FROM configurator_schacht")
                        count = cursor.fetchone()[0]
                        if count > 0:
                            # Data already exists, skip seeding
                            return
                    except Exception:
                        # Table doesn't exist yet or error, skip seeding
                        return
                
                # Database is empty, run seeding
                call_command('import_csv_data', '--force', verbosity=0)
                call_command('add_missing_probes', verbosity=0)
            except Exception:
                # Silently fail if there's an error
                # The commands can be run manually if needed
                pass
