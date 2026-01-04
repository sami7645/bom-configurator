"""
Custom management command that runs migrations and then seeds the database.
Usage: python manage.py migrate_and_seed
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Run migrations and then seed the database with CSV data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-seed',
            action='store_true',
            help='Skip seeding after migration',
        )
        parser.add_argument(
            '--fake',
            action='store_true',
            help='Mark migrations as run without actually running them',
        )
        parser.add_argument(
            '--fake-initial',
            action='store_true',
            help='Detect if tables already exist and fake-apply initial migrations',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Running migrations...'))
        
        # Run migrations
        migrate_options = {}
        if options['fake']:
            migrate_options['fake'] = True
        if options['fake_initial']:
            migrate_options['fake_initial'] = True
        
        call_command('migrate', **migrate_options)
        
        if not options['no_seed']:
            self.stdout.write(self.style.SUCCESS('Seeding database...'))
            
            # Run CSV import
            try:
                call_command('import_csv_data', '--force')
                self.stdout.write(self.style.SUCCESS('✓ CSV data imported'))
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Error importing CSV data: {str(e)}')
                )
            
            # Run missing probes
            try:
                call_command('add_missing_probes')
                self.stdout.write(self.style.SUCCESS('✓ Missing probes added'))
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Error adding missing probes: {str(e)}')
                )
            
            self.stdout.write(self.style.SUCCESS('\n✓ Database seeded successfully!'))
        else:
            self.stdout.write(self.style.WARNING('Skipping seeding (--no-seed flag)'))

