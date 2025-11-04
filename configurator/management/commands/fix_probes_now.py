from django.core.management.base import BaseCommand
from configurator.models import Sondengroesse, Schacht, HVB
from decimal import Decimal

class Command(BaseCommand):
    help = 'Immediately fix probe combinations for dropdown'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔧 Starting probe fix...'))
        
        # First, let's see what we have
        total_probes_before = Sondengroesse.objects.count()
        total_schacht = Schacht.objects.count()
        total_hvb = HVB.objects.count()
        
        self.stdout.write(f'📊 Current database status:')
        self.stdout.write(f'   - Probes: {total_probes_before}')
        self.stdout.write(f'   - Schacht types: {total_schacht}')
        self.stdout.write(f'   - HVB sizes: {total_hvb}')
        
        if total_schacht == 0 or total_hvb == 0:
            self.stdout.write(self.style.ERROR('❌ Missing basic data! Run: python manage.py import_csv_data'))
            return
        
        # Show what Schacht and HVB we have
        schacht_list = list(Schacht.objects.values_list('schachttyp', flat=True))
        hvb_list = list(HVB.objects.values_list('hauptverteilerbalken', flat=True))
        
        self.stdout.write(f'📋 Available Schacht types: {schacht_list[:10]}')
        self.stdout.write(f'📋 Available HVB sizes: {hvb_list[:10]}')
        
        # Add comprehensive probe data
        probe_combinations = [
            # GN X1 combinations
            {'durchmesser_sonde': '32', 'artikelnummer': '2000488', 'artikelbezeichnung': 'Rohr - PE 100-RC - 32', 'schachttyp': 'GN X1', 'hvb_size': '63', 'sondenanzahl_min': 5, 'sondenanzahl_max': 20, 'vorlauf_laenge': Decimal('0.280'), 'ruecklauf_laenge': Decimal('0.365')},
            {'durchmesser_sonde': '40', 'artikelnummer': '2000489', 'artikelbezeichnung': 'Rohr - PE 100-RC - 40', 'schachttyp': 'GN X1', 'hvb_size': '75', 'sondenanzahl_min': 5, 'sondenanzahl_max': 25, 'vorlauf_laenge': Decimal('0.280'), 'ruecklauf_laenge': Decimal('0.365')},
            {'durchmesser_sonde': '50', 'artikelnummer': '2000490', 'artikelbezeichnung': 'Rohr - PE 100-RC - 50', 'schachttyp': 'GN X1', 'hvb_size': '90', 'sondenanzahl_min': 5, 'sondenanzahl_max': 30, 'vorlauf_laenge': Decimal('0.280'), 'ruecklauf_laenge': Decimal('0.365')},
            
            # GN X2 combinations
            {'durchmesser_sonde': '32', 'artikelnummer': '2000488', 'artikelbezeichnung': 'Rohr - PE 100-RC - 32', 'schachttyp': 'GN X2', 'hvb_size': '90', 'sondenanzahl_min': 6, 'sondenanzahl_max': 25, 'vorlauf_laenge': Decimal('0.280'), 'ruecklauf_laenge': Decimal('0.365')},
            {'durchmesser_sonde': '40', 'artikelnummer': '2000489', 'artikelbezeichnung': 'Rohr - PE 100-RC - 40', 'schachttyp': 'GN X2', 'hvb_size': '110', 'sondenanzahl_min': 6, 'sondenanzahl_max': 30, 'vorlauf_laenge': Decimal('0.280'), 'ruecklauf_laenge': Decimal('0.365')},
            
            # GN X3 combinations
            {'durchmesser_sonde': '32', 'artikelnummer': '2000488', 'artikelbezeichnung': 'Rohr - PE 100-RC - 32', 'schachttyp': 'GN X3', 'hvb_size': '110', 'sondenanzahl_min': 10, 'sondenanzahl_max': 50, 'vorlauf_laenge': Decimal('0.280'), 'ruecklauf_laenge': Decimal('0.365')},
            {'durchmesser_sonde': '40', 'artikelnummer': '2000489', 'artikelbezeichnung': 'Rohr - PE 100-RC - 40', 'schachttyp': 'GN X3', 'hvb_size': '125', 'sondenanzahl_min': 10, 'sondenanzahl_max': 60, 'vorlauf_laenge': Decimal('0.280'), 'ruecklauf_laenge': Decimal('0.365')},
            {'durchmesser_sonde': '50', 'artikelnummer': '2000490', 'artikelbezeichnung': 'Rohr - PE 100-RC - 50', 'schachttyp': 'GN X3', 'hvb_size': '140', 'sondenanzahl_min': 10, 'sondenanzahl_max': 70, 'vorlauf_laenge': Decimal('0.280'), 'ruecklauf_laenge': Decimal('0.365')},
            
            # GN X4 combinations
            {'durchmesser_sonde': '40', 'artikelnummer': '2000489', 'artikelbezeichnung': 'Rohr - PE 100-RC - 40', 'schachttyp': 'GN X4', 'hvb_size': '160', 'sondenanzahl_min': 15, 'sondenanzahl_max': 80, 'vorlauf_laenge': Decimal('0.280'), 'ruecklauf_laenge': Decimal('0.365')},
            {'durchmesser_sonde': '50', 'artikelnummer': '2000490', 'artikelbezeichnung': 'Rohr - PE 100-RC - 50', 'schachttyp': 'GN X4', 'hvb_size': '180', 'sondenanzahl_min': 15, 'sondenanzahl_max': 100, 'vorlauf_laenge': Decimal('0.280'), 'ruecklauf_laenge': Decimal('0.365')},
            
            # GN 2 combinations
            {'durchmesser_sonde': '32', 'artikelnummer': '2000488', 'artikelbezeichnung': 'Rohr - PE 100-RC - 32', 'schachttyp': 'GN 2', 'hvb_size': '63', 'sondenanzahl_min': 5, 'sondenanzahl_max': 15, 'vorlauf_laenge': Decimal('0.265'), 'ruecklauf_laenge': Decimal('0.365')},
            {'durchmesser_sonde': '40', 'artikelnummer': '2000489', 'artikelbezeichnung': 'Rohr - PE 100-RC - 40', 'schachttyp': 'GN 2', 'hvb_size': '75', 'sondenanzahl_min': 5, 'sondenanzahl_max': 20, 'vorlauf_laenge': Decimal('0.265'), 'ruecklauf_laenge': Decimal('0.365')},
            
            # GN R Medium combinations
            {'durchmesser_sonde': '32', 'artikelnummer': '2000488', 'artikelbezeichnung': 'Rohr - PE 100-RC - 32', 'schachttyp': 'GN R Medium', 'hvb_size': '63', 'sondenanzahl_min': 3, 'sondenanzahl_max': 8, 'vorlauf_laenge': Decimal('0.200'), 'ruecklauf_laenge': Decimal('0.300')},
            {'durchmesser_sonde': '40', 'artikelnummer': '2000489', 'artikelbezeichnung': 'Rohr - PE 100-RC - 40', 'schachttyp': 'GN R Medium', 'hvb_size': '75', 'sondenanzahl_min': 3, 'sondenanzahl_max': 10, 'vorlauf_laenge': Decimal('0.200'), 'ruecklauf_laenge': Decimal('0.300')},
            
            # GN R Mini combinations
            {'durchmesser_sonde': '32', 'artikelnummer': '2000488', 'artikelbezeichnung': 'Rohr - PE 100-RC - 32', 'schachttyp': 'GN R Mini', 'hvb_size': '63', 'sondenanzahl_min': 2, 'sondenanzahl_max': 5, 'vorlauf_laenge': Decimal('0.150'), 'ruecklauf_laenge': Decimal('0.250')},
            
            # GN 1 combinations
            {'durchmesser_sonde': '40', 'artikelnummer': '2000489', 'artikelbezeichnung': 'Rohr - PE 100-RC - 40', 'schachttyp': 'GN 1', 'hvb_size': '75', 'sondenanzahl_min': 8, 'sondenanzahl_max': 15, 'vorlauf_laenge': Decimal('0.265'), 'ruecklauf_laenge': Decimal('0.365')},
        ]
        
        added_count = 0
        errors = []
        
        for probe_data in probe_combinations:
            try:
                # Get the actual model objects
                schacht = Schacht.objects.filter(schachttyp=probe_data['schachttyp']).first()
                hvb = HVB.objects.filter(hauptverteilerbalken=probe_data['hvb_size']).first()
                
                if not schacht:
                    errors.append(f"❌ Schachttyp '{probe_data['schachttyp']}' not found")
                    continue
                    
                if not hvb:
                    errors.append(f"❌ HVB size '{probe_data['hvb_size']}' not found")
                    continue
                
                # Check if combination already exists
                existing = Sondengroesse.objects.filter(
                    durchmesser_sonde=probe_data['durchmesser_sonde'],
                    schachttyp=schacht,
                    hvb_size=hvb
                ).first()
                
                if not existing:
                    Sondengroesse.objects.create(
                        durchmesser_sonde=probe_data['durchmesser_sonde'],
                        artikelnummer=probe_data['artikelnummer'],
                        artikelbezeichnung=probe_data['artikelbezeichnung'],
                        schachttyp=schacht,
                        hvb_size=hvb,
                        bauform='',  # Default empty
                        sondenanzahl_min=probe_data['sondenanzahl_min'],
                        sondenanzahl_max=probe_data['sondenanzahl_max'],
                        vorlauf_laenge=probe_data['vorlauf_laenge'],
                        ruecklauf_laenge=probe_data['ruecklauf_laenge'],
                        vorlauf_formel='',  # Default empty
                        ruecklauf_formel='',  # Default empty
                        hinweis=''  # Default empty
                    )
                    added_count += 1
                    self.stdout.write(f'✅ Added: {probe_data["schachttyp"]} + {probe_data["hvb_size"]}mm + {probe_data["durchmesser_sonde"]}mm')
                    
            except Exception as e:
                errors.append(f"❌ Error with {probe_data['schachttyp']} + {probe_data['hvb_size']}mm: {str(e)}")
        
        # Show results
        total_probes_after = Sondengroesse.objects.count()
        
        self.stdout.write(self.style.SUCCESS(f'🎉 Probe fix completed!'))
        self.stdout.write(f'📊 Results:')
        self.stdout.write(f'   - Probes before: {total_probes_before}')
        self.stdout.write(f'   - Probes after: {total_probes_after}')
        self.stdout.write(f'   - Added: {added_count}')
        
        if errors:
            self.stdout.write(self.style.WARNING(f'⚠️  Errors encountered:'))
            for error in errors[:5]:  # Show first 5 errors
                self.stdout.write(f'   {error}')
        
        # Test a few combinations
        self.stdout.write(f'🧪 Testing combinations:')
        test_cases = [
            ('GN X1', '75'),
            ('GN X3', '125'),
            ('GN 2', '63')
        ]
        
        for schacht_name, hvb_size in test_cases:
            probes = Sondengroesse.objects.filter(
                schachttyp__schachttyp=schacht_name,
                hvb_size__hauptverteilerbalken=hvb_size
            ).values_list('durchmesser_sonde', flat=True)
            
            probe_list = list(probes)
            self.stdout.write(f'   {schacht_name} + {hvb_size}mm: {probe_list}')
        
        self.stdout.write(self.style.SUCCESS('✨ Done! Try the configurator now.'))
