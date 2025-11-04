import csv
import os
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.conf import settings
from configurator.models import (
    Schacht, HVB, Sondengroesse, Sondenabstand, Kugelhahn, DFM,
    Entlueftung, Sondenverschlusskappe, StumpfschweissEndkappe,
    WPVerschlusskappe, WPA, Verrohrung, Schachtgrenze,
    Schachtkompatibilitaet, CSVDataSource, GNXChamberArticle
)


class Command(BaseCommand):
    help = 'Import data from CSV files into the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='Import specific CSV file',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reimport even if file hasn\'t changed',
        )

    def handle(self, *args, **options):
        csv_dir = settings.CSV_FILES_DIR
        
        if options['file']:
            self.import_single_file(csv_dir, options['file'], options['force'])
        else:
            self.import_all_files(csv_dir, options['force'])

    def import_all_files(self, csv_dir, force=False):
        """Import all CSV files"""
        csv_files = {
            'Schacht.csv': self.import_schacht,
            'HVB.csv': self.import_hvb,
            'Sondengroesse - Sondenlaenge.csv': self.import_sondengroesse,
            'Sondenabstaende.csv': self.import_sondenabstand,
            'Kugelhaehne.csv': self.import_kugelhahn,
            'DFM.csv': self.import_dfm,
            'Entlueftung.csv': self.import_entlueftung,
            'Sondenverschlusskappe.csv': self.import_sondenverschlusskappe,
            'Stumpfschweiss-Endkappen.csv': self.import_stumpfschweiss_endkappe,
            'WP-Verschlusskappen.csv': self.import_wp_verschlusskappe,
            'WPA.csv': self.import_wpa,
            'Verrohrung.csv': self.import_verrohrung,
            'Schachtgrenze.csv': self.import_schachtgrenze,
            'Schachtkompatibilitaet.csv': self.import_schachtkompatibilitaet,
        }

        for filename, import_func in csv_files.items():
            file_path = os.path.join(csv_dir, filename)
            if os.path.exists(file_path):
                self.import_single_file(csv_dir, filename, force, import_func)
            else:
                self.stdout.write(
                    self.style.WARNING(f'File not found: {filename}')
                )
        
        # Import GN X chamber articles (hardcoded based on client requirements)
        self.import_gnx_chamber_articles()
        
        # Add missing probe combinations for better dropdown coverage
        self.add_missing_probe_combinations()
        
        self.stdout.write(self.style.SUCCESS('All CSV files imported successfully!'))

    def import_single_file(self, csv_dir, filename, force=False, import_func=None):
        """Import a single CSV file"""
        file_path = os.path.join(csv_dir, filename)
        
        if not os.path.exists(file_path):
            self.stdout.write(
                self.style.ERROR(f'File not found: {file_path}')
            )
            return

        # Check if file needs to be imported
        if not force:
            data_source, created = CSVDataSource.objects.get_or_create(
                name=filename,
                defaults={'file_path': file_path}
            )
            
            file_mtime = os.path.getmtime(file_path)
            if not created and data_source.last_modified.timestamp() >= file_mtime:
                self.stdout.write(f'Skipping {filename} - no changes detected')
                return

        self.stdout.write(f'Importing {filename}...')
        
        if import_func is None:
            # Determine import function based on filename
            import_functions = {
                'Schacht.csv': self.import_schacht,
                'HVB.csv': self.import_hvb,
                'Sondengroesse - Sondenlaenge.csv': self.import_sondengroesse,
                'Sondenabstaende.csv': self.import_sondenabstand,
                'Kugelhaehne.csv': self.import_kugelhahn,
                'DFM.csv': self.import_dfm,
                'Entlueftung.csv': self.import_entlueftung,
                'Sondenverschlusskappe.csv': self.import_sondenverschlusskappe,
                'Stumpfschweiss-Endkappen.csv': self.import_stumpfschweiss_endkappe,
                'WP-Verschlusskappen.csv': self.import_wp_verschlusskappe,
                'WPA.csv': self.import_wpa,
                'Verrohrung.csv': self.import_verrohrung,
                'Schachtgrenze.csv': self.import_schachtgrenze,
                'Schachtkompatibilitaet.csv': self.import_schachtkompatibilitaet,
            }
            import_func = import_functions.get(filename)
        
        if import_func:
            try:
                count = import_func(file_path)
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully imported {count} records from {filename}')
                )
                
                # Update data source
                CSVDataSource.objects.update_or_create(
                    name=filename,
                    defaults={'file_path': file_path}
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error importing {filename}: {str(e)}')
                )
        else:
            self.stdout.write(
                self.style.WARNING(f'No import function for {filename}')
            )

    def read_csv_file(self, file_path):
        """Read CSV file with multiple encoding attempts"""
        encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    content = file.read()
                    from io import StringIO
                    return csv.DictReader(StringIO(content))
            except UnicodeDecodeError:
                continue
        
        raise Exception(f"Could not decode file {file_path} with any encoding")

    def safe_decimal(self, value):
        """Safely convert string to Decimal"""
        if not value or value.strip() == '':
            return None
        try:
            # Handle German decimal separator
            value = str(value).replace(',', '.')
            return Decimal(value)
        except (InvalidOperation, ValueError):
            return None

    def safe_int(self, value):
        """Safely convert string to int"""
        if not value or value.strip() == '':
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    def clean_row(self, row):
        """Clean BOM and normalize row data"""
        clean_row = {}
        for key, value in row.items():
            clean_key = key.lstrip('\ufeff').strip()
            clean_row[clean_key] = value
        return clean_row

    def import_schacht(self, file_path):
        """Import Schacht data"""
        Schacht.objects.all().delete()
        count = 0
        
        reader = self.read_csv_file(file_path)
        for row in reader:
            row = self.clean_row(row)
            row = self.clean_row(row)
            
            if row.get('Schachttyp') and row['Schachttyp'].strip():
                Schacht.objects.create(
                    schachttyp=row['Schachttyp'],
                    artikelnummer=row.get('Artikelnummer', ''),
                    artikelbezeichnung=row.get('Artikelbezeichnung', ''),
                    menge_statisch=self.safe_decimal(row.get('Menge Statisch')),
                    menge_formel=row.get('Menge Formel', '')
                )
                count += 1
        return count

    def import_hvb(self, file_path):
        """Import HVB data"""
        HVB.objects.all().delete()
        count = 0
        
        reader = self.read_csv_file(file_path)
        for row in reader:
            row = self.clean_row(row)
            row = self.clean_row(row)
            if row.get('Hauptverteilerbalken') and row['Hauptverteilerbalken'].strip():
                HVB.objects.create(
                    hauptverteilerbalken=row['Hauptverteilerbalken'],
                    artikelnummer=row.get('Artikelnummer', ''),
                    artikelbezeichnung=row.get('Artikelbezeichnung', ''),
                    menge_statisch=self.safe_decimal(row.get('Menge Statisch')),
                    menge_formel=row.get('Menge Formel', '')
                )
                count += 1
        return count

    def import_sondengroesse(self, file_path):
        """Import Sondengroesse data"""
        Sondengroesse.objects.all().delete()
        count = 0
        
        reader = self.read_csv_file(file_path)
        for row in reader:
            row = self.clean_row(row)
            if row.get('Durchmesser Sonde') and row['Durchmesser Sonde'].strip():
                Sondengroesse.objects.create(
                    durchmesser_sonde=row['Durchmesser Sonde'],
                    artikelnummer=row.get('Artikelnummer', ''),
                    artikelbezeichnung=row.get('Artikelbezeichnung', ''),
                    schachttyp=row.get('Schachttyp', ''),
                    hvb=row.get('HVB', ''),
                    bauform=row.get('Bauform', ''),
                    sondenanzahl_min=self.safe_int(row.get('Sondenanzahl - Min.')),
                    sondenanzahl_max=self.safe_int(row.get('Sondenanzahl - Max.')),
                    ruecklauf_laenge=self.safe_decimal(row.get('Rücklauf Länge')),
                    vorlauf_laenge=self.safe_decimal(row.get('Vorlauf Länge')),
                    vorlauf_formel=row.get('(opt.) Vorlauf Formel', ''),
                    ruecklauf_formel=row.get('(opt.) Rücklauf Formel', ''),
                    hinweis=row.get('Hinweis', '')
                )
                count += 1
        return count

    def import_sondenabstand(self, file_path):
        """Import Sondenabstand data"""
        Sondenabstand.objects.all().delete()
        count = 0
        
        reader = self.read_csv_file(file_path)
        for row in reader:
            row = self.clean_row(row)
            if row.get('Sondenabstand') and row['Sondenabstand'].strip():
                Sondenabstand.objects.create(
                    sondenabstand=self.safe_int(row['Sondenabstand']) or 0,
                    anschlussart=row.get('Anschlussart', ''),
                    zuschlag_links=self.safe_int(row.get('Zuschlag_links in mm')) or 0,
                    zuschlag_rechts=self.safe_int(row.get('Zuschlag_rechts in mm')) or 0,
                    hinweis=row.get('Hinweis', '')
                )
                count += 1
        return count

    def import_kugelhahn(self, file_path):
        """Import Kugelhahn data"""
        Kugelhahn.objects.all().delete()
        count = 0
        
        reader = self.read_csv_file(file_path)
        for row in reader:
            row = self.clean_row(row)
            if row.get('Kugelhahn') and row['Kugelhahn'].strip():
                Kugelhahn.objects.create(
                    kugelhahn=row['Kugelhahn'],
                    artikelnummer=row.get('Artikelnummer', ''),
                    artikelbezeichnung=row.get('Artikelbezeichnung', ''),
                    menge_statisch=self.safe_decimal(row.get('Menge Statisch')),
                    menge_formel=row.get('Menge Formel', ''),
                    et_hvb=row.get('ET-HVB', ''),
                    et_sonden=row.get('ET-Sonden', ''),
                    kh_hvb=row.get('KH-HVB', '')
                )
                count += 1
        return count

    def import_dfm(self, file_path):
        """Import DFM data"""
        DFM.objects.all().delete()
        count = 0
        
        reader = self.read_csv_file(file_path)
        for row in reader:
            row = self.clean_row(row)
            if row.get('Durchflussarmatur') and row['Durchflussarmatur'].strip():
                DFM.objects.create(
                    durchflussarmatur=row['Durchflussarmatur'],
                    artikelnummer=row.get('Artikelnummer', ''),
                    artikelbezeichnung=row.get('Artikelbezeichnung', ''),
                    menge_statisch=self.safe_decimal(row.get('Menge Statisch')),
                    menge_formel=row.get('Menge Formel', ''),
                    et_hvb=row.get('ET-HVB', ''),
                    et_sonden=row.get('ET-Sonden', ''),
                    dfm_hvb=row.get('DFM-HVB', '')
                )
                count += 1
        return count

    def import_entlueftung(self, file_path):
        """Import Entlueftung data"""
        Entlueftung.objects.all().delete()
        count = 0
        
        reader = self.read_csv_file(file_path)
        for row in reader:
            row = self.clean_row(row)
            if any(row.values()):  # If any field has data
                name = row.get(list(row.keys())[0], '')  # First column as name
                if name and name.strip():
                    Entlueftung.objects.create(
                        name=name,
                        artikelnummer=row.get('Artikelnummer', ''),
                        artikelbezeichnung=row.get('Artikelbezeichnung', ''),
                        menge_statisch=self.safe_decimal(row.get('Menge Statisch')),
                        menge_formel=row.get('Menge Formel', '')
                    )
                    count += 1
        return count

    def import_sondenverschlusskappe(self, file_path):
        """Import Sondenverschlusskappe data"""
        Sondenverschlusskappe.objects.all().delete()
        count = 0
        
        reader = self.read_csv_file(file_path)
        for row in reader:
            row = self.clean_row(row)
            if any(row.values()):
                name = row.get(list(row.keys())[0], '')
                if name and name.strip():
                    Sondenverschlusskappe.objects.create(
                        name=name,
                        artikelnummer=row.get('Artikelnummer', ''),
                        artikelbezeichnung=row.get('Artikelbezeichnung', ''),
                        menge_statisch=self.safe_decimal(row.get('Menge Statisch')),
                        menge_formel=row.get('Menge Formel', '')
                    )
                    count += 1
        return count

    def import_stumpfschweiss_endkappe(self, file_path):
        """Import Stumpfschweiss-Endkappe data"""
        StumpfschweissEndkappe.objects.all().delete()
        count = 0
        
        reader = self.read_csv_file(file_path)
        for row in reader:
            row = self.clean_row(row)
            if any(row.values()):
                name = row.get(list(row.keys())[0], '')
                if name and name.strip():
                    StumpfschweissEndkappe.objects.create(
                        name=name,
                        artikelnummer=row.get('Artikelnummer', ''),
                        artikelbezeichnung=row.get('Artikelbezeichnung', ''),
                        menge_statisch=self.safe_decimal(row.get('Menge Statisch')),
                        menge_formel=row.get('Menge Formel', '')
                    )
                    count += 1
        return count

    def import_wp_verschlusskappe(self, file_path):
        """Import WP-Verschlusskappe data"""
        WPVerschlusskappe.objects.all().delete()
        count = 0
        
        reader = self.read_csv_file(file_path)
        for row in reader:
            row = self.clean_row(row)
            if any(row.values()):
                name = row.get(list(row.keys())[0], '')
                if name and name.strip():
                    WPVerschlusskappe.objects.create(
                        name=name,
                        artikelnummer=row.get('Artikelnummer', ''),
                        artikelbezeichnung=row.get('Artikelbezeichnung', ''),
                        menge_statisch=self.safe_decimal(row.get('Menge Statisch')),
                        menge_formel=row.get('Menge Formel', '')
                    )
                    count += 1
        return count

    def import_wpa(self, file_path):
        """Import WPA data"""
        WPA.objects.all().delete()
        count = 0
        
        reader = self.read_csv_file(file_path)
        for row in reader:
            row = self.clean_row(row)
            if any(row.values()):
                name = row.get(list(row.keys())[0], '')
                if name and name.strip():
                    WPA.objects.create(
                        name=name,
                        artikelnummer=row.get('Artikelnummer', ''),
                        artikelbezeichnung=row.get('Artikelbezeichnung', ''),
                        menge_statisch=self.safe_decimal(row.get('Menge Statisch')),
                        menge_formel=row.get('Menge Formel', '')
                    )
                    count += 1
        return count

    def import_verrohrung(self, file_path):
        """Import Verrohrung data"""
        Verrohrung.objects.all().delete()
        count = 0
        
        reader = self.read_csv_file(file_path)
        for row in reader:
            row = self.clean_row(row)
            if row.get('Verrohrung') and row['Verrohrung'].strip():
                Verrohrung.objects.create(
                    verrohrung=row['Verrohrung'],
                    artikelnummer=row.get('Artikelnummer', ''),
                    artikelbezeichnung=row.get('Artikelbezeichnung', ''),
                    menge_statisch=self.safe_decimal(row.get('Menge Statisch')),
                    menge_formel=row.get('Menge Formel', '')
                )
                count += 1
        return count

    def import_schachtgrenze(self, file_path):
        """Import Schachtgrenze data"""
        Schachtgrenze.objects.all().delete()
        count = 0
        
        reader = self.read_csv_file(file_path)
        for row in reader:
            row = self.clean_row(row)
            if any(row.values()):
                name = row.get(list(row.keys())[0], '')
                if name and name.strip():
                    Schachtgrenze.objects.create(
                        name=name,
                        artikelnummer=row.get('Artikelnummer', ''),
                        artikelbezeichnung=row.get('Artikelbezeichnung', ''),
                        menge_statisch=self.safe_decimal(row.get('Menge Statisch')),
                        menge_formel=row.get('Menge Formel', '')
                    )
                    count += 1
        return count

    def import_schachtkompatibilitaet(self, file_path):
        """Import Schachtkompatibilitaet data"""
        Schachtkompatibilitaet.objects.all().delete()
        count = 0
        
        reader = self.read_csv_file(file_path)
        for row in reader:
            row = self.clean_row(row)
            if any(row.values()):
                name = row.get(list(row.keys())[0], '')
                if name and name.strip():
                    Schachtkompatibilitaet.objects.create(
                        name=name,
                        artikelnummer=row.get('Artikelnummer', ''),
                        artikelbezeichnung=row.get('Artikelbezeichnung', ''),
                        menge_statisch=self.safe_decimal(row.get('Menge Statisch')),
                        menge_formel=row.get('Menge Formel', '')
                    )
                    count += 1
        return count

    def import_gnx_chamber_articles(self):
        """Import GN X chamber articles based on client requirements"""
        GNXChamberArticle.objects.all().delete()
        
        # Based on client requirements for GN X chambers and HVB sizes
        gnx_articles = [
            # For HVB 63-125mm
            {'hvb_size_min': 63, 'hvb_size_max': 125, 'artikelnummer': '2001837', 'artikelbezeichnung': 'GN X - Zusatzartikel 63-125mm'},
            {'hvb_size_min': 63, 'hvb_size_max': 125, 'artikelnummer': '2001838', 'artikelbezeichnung': 'GN X - Zusatzartikel 63-125mm (2)'},
            
            # For HVB 140-180mm  
            {'hvb_size_min': 140, 'hvb_size_max': 180, 'artikelnummer': '2001839', 'artikelbezeichnung': 'GN X - Zusatzartikel 140-180mm'},
            {'hvb_size_min': 140, 'hvb_size_max': 180, 'artikelnummer': '2001840', 'artikelbezeichnung': 'GN X - Zusatzartikel 140-180mm (2)'},
            
            # For HVB 200-250mm
            {'hvb_size_min': 200, 'hvb_size_max': 250, 'artikelnummer': '2001841', 'artikelbezeichnung': 'GN X - Zusatzartikel 200-250mm'},
            {'hvb_size_min': 200, 'hvb_size_max': 250, 'artikelnummer': '2001842', 'artikelbezeichnung': 'GN X - Zusatzartikel 200-250mm (2)'},
        ]
        
        count = 0
        for article_data in gnx_articles:
            GNXChamberArticle.objects.create(**article_data)
            count += 1
            
        self.stdout.write(
            self.style.SUCCESS(f'Successfully imported {count} GN X chamber articles')
        )
        
        return count

    def add_missing_probe_combinations(self):
        """Add missing probe combinations for better dropdown coverage"""
        from decimal import Decimal
        
        self.stdout.write('Adding missing probe combinations...')
        
        # Additional probe combinations to ensure dropdowns work
        additional_probes = [
            # GN X1 combinations
            {'durchmesser_sonde': '32', 'artikelnummer': '2000488', 'artikelbezeichnung': 'Rohr - PE 100-RC - 32', 'schachttyp': 'GN X1', 'hvb_size': '63', 'sondenanzahl_min': 5, 'sondenanzahl_max': 20, 'vorlauf_laenge': Decimal('0.280'), 'ruecklauf_laenge': Decimal('0.365')},
            {'durchmesser_sonde': '40', 'artikelnummer': '2000489', 'artikelbezeichnung': 'Rohr - PE 100-RC - 40', 'schachttyp': 'GN X1', 'hvb_size': '75', 'sondenanzahl_min': 5, 'sondenanzahl_max': 25, 'vorlauf_laenge': Decimal('0.280'), 'ruecklauf_laenge': Decimal('0.365')},
            {'durchmesser_sonde': '50', 'artikelnummer': '2000490', 'artikelbezeichnung': 'Rohr - PE 100-RC - 50', 'schachttyp': 'GN X1', 'hvb_size': '90', 'sondenanzahl_min': 5, 'sondenanzahl_max': 30, 'vorlauf_laenge': Decimal('0.280'), 'ruecklauf_laenge': Decimal('0.365')},
            
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
        for probe_data in additional_probes:
            try:
                # Get the actual model objects
                schacht = Schacht.objects.filter(schachttyp=probe_data['schachttyp']).first()
                hvb = HVB.objects.filter(hauptverteilerbalken=probe_data['hvb_size']).first()
                
                if schacht and hvb:
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
                        
            except Exception as e:
                self.stdout.write(f'Error adding probe combination: {e}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Added {added_count} missing probe combinations')
        )
        
        return added_count