import csv
import os
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.conf import settings
from configurator.models import (
    Schacht, HVB, Sondengroesse, Sondenabstand, SondenDurchmesser, Kugelhahn, DFM,
    Entlueftung, Sondenverschlusskappe, StumpfschweissEndkappe,
    WPVerschlusskappe, WPA, Verrohrung, Schachtgrenze,
    Schachtkompatibilitaet, CSVDataSource, GNXChamberArticle, HVBStuetze
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
            'Sonden Durchmesser.csv': self.import_sonden_durchmesser,
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
            'GNXChamberArticle.csv': self.import_gnx_chamber_articles_csv,
            'GN X-Series - Extra Articles.csv': self.import_gnx_extra_articles_csv,
            'AdditionalProbeCombinations.csv': self.import_additional_probe_combinations_csv,
        }

        for filename, import_func in csv_files.items():
            file_path = os.path.join(csv_dir, filename)
            if os.path.exists(file_path):
                self.import_single_file(csv_dir, filename, force, import_func)
            else:
                self.stdout.write(
                    self.style.WARNING(f'File not found: {filename}')
                )
        
        
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
                'Sonden Durchmesser.csv': self.import_sonden_durchmesser,
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
                'GNXChamberArticle.csv': self.import_gnx_chamber_articles_csv,
                'GN X-Series - Extra Articles.csv': self.import_gnx_extra_articles_csv,
                'AdditionalProbeCombinations.csv': self.import_additional_probe_combinations_csv,
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

    def import_sonden_durchmesser(self, file_path):
        """Import Sonden Durchmesser data - matrix format where columns are schacht types and rows are diameters"""
        SondenDurchmesser.objects.all().delete()
        count = 0
        
        # Read CSV file manually to handle matrix format
        import csv
        encodings = ['utf-8-sig', 'utf-8', 'latin1', 'cp1252']
        reader = None
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding, newline='') as f:
                    reader = list(csv.reader(f))
                    break
            except UnicodeDecodeError:
                continue
        
        if not reader:
            self.stdout.write(self.style.ERROR(f'Could not read file: {file_path}'))
            return 0
        
        # First row contains schacht types (columns)
        if len(reader) == 0:
            return 0
        
        schacht_types = [col.strip() for col in reader[0] if col.strip()]
        
        # Subsequent rows contain probe diameters for each schacht type
        for row_idx in range(1, len(reader)):
            row = reader[row_idx]
            for col_idx, durchmesser in enumerate(row):
                if col_idx < len(schacht_types) and durchmesser and durchmesser.strip():
                    schachttyp = schacht_types[col_idx]
                    durchmesser_value = durchmesser.strip()
                    # Only create if diameter is not empty
                    if durchmesser_value:
                        SondenDurchmesser.objects.get_or_create(
                            schachttyp=schachttyp,
                            durchmesser=durchmesser_value,
                            defaults={}
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
                        menge_formel=row.get('Menge Formel', ''),
                        et_hvb=row.get('ET-HVB', '')
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
                    durchmesser = row.get('Sondenverschlusskappe') or name
                    Sondenverschlusskappe.objects.create(
                        name=name,
                        artikelnummer=row.get('Artikelnummer', ''),
                        artikelbezeichnung=row.get('Artikelbezeichnung', ''),
                        menge_statisch=self.safe_decimal(row.get('Menge Statisch')),
                        menge_formel=row.get('Menge Formel', ''),
                        sonden_durchmesser=str(durchmesser).strip()
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
                    hvb_size = row.get('HVB')
                    artikelbezeichnung = row.get('Artikelbezeichnung', '')
                    StumpfschweissEndkappe.objects.create(
                        name=name,
                        artikelnummer=row.get('Artikelnummer', ''),
                        artikelbezeichnung=artikelbezeichnung,
                        menge_statisch=self.safe_decimal(row.get('Menge Statisch')),
                        menge_formel=row.get('Menge Formel', ''),
                        hvb_durchmesser=str(hvb_size).strip() if hvb_size else None,
                        is_short_version='kurz' in artikelbezeichnung.lower()
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
            schachttyp = row.get('Schachttyp', '').strip()
            if schachttyp:
                max_sondenanzahl = self.safe_int(row.get('Max Sondenanzahl'))
                erlaubte_hvb = row.get('Erlaubte HVB', '').strip()
                hinweis = row.get('Hinweis', '').strip()
                
                Schachtgrenze.objects.create(
                    schachttyp=schachttyp,
                    max_sondenanzahl=max_sondenanzahl,
                    erlaubte_hvb=erlaubte_hvb,
                    hinweis=hinweis
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

    def import_gnx_chamber_articles_csv(self, file_path):
        """Import GN X chamber articles from CSV file"""
        GNXChamberArticle.objects.all().delete()
        
        count = 0
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    GNXChamberArticle.objects.create(
                        hvb_size_min=int(row['hvb_size_min']),
                        hvb_size_max=int(row['hvb_size_max']),
                        artikelnummer=row['artikelnummer'].strip(),
                        artikelbezeichnung=row['artikelbezeichnung'].strip()
                    )
                    count += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'Error importing GN X chamber article {row.get("artikelnummer", "unknown")}: {e}')
                    )
        
        return count

    def import_additional_probe_combinations_csv(self, file_path):
        """Import additional probe combinations from CSV file (only adds if combination doesn't exist)"""
        from decimal import Decimal
        
        added_count = 0
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # Check if combination already exists
                    existing = Sondengroesse.objects.filter(
                        durchmesser_sonde=row['durchmesser_sonde'].strip(),
                        schachttyp=row['schachttyp'].strip(),
                        hvb=row['hvb_size'].strip()
                    ).first()
                    
                    if not existing:
                        Sondengroesse.objects.create(
                            durchmesser_sonde=row['durchmesser_sonde'].strip(),
                            artikelnummer=row['artikelnummer'].strip(),
                            artikelbezeichnung=row['artikelbezeichnung'].strip(),
                            schachttyp=row['schachttyp'].strip(),
                            hvb=row['hvb_size'].strip(),
                            bauform='',
                            sondenanzahl_min=int(row['sondenanzahl_min']),
                            sondenanzahl_max=int(row['sondenanzahl_max']),
                            vorlauf_laenge=Decimal(row['vorlauf_laenge']),
                            ruecklauf_laenge=Decimal(row['ruecklauf_laenge']),
                            vorlauf_formel='',
                            ruecklauf_formel='',
                            hinweis=''
                        )
                        added_count += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'Error importing additional probe combination: {e}')
                    )
        
        return added_count
    
    def import_gnx_extra_articles_csv(self, file_path):
        """Import GN X-Series Extra Articles (HVB Stütze) from CSV file"""
        import re
        HVBStuetze.objects.all().delete()
        
        count = 0
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
            # Skip first line if it's not a proper header
            start_line = 0
            if lines and 'Xentral' in lines[0]:
                start_line = 1
            
            # Find the header line (should contain "Nummer" and "Artikel")
            header_line = None
            for i in range(start_line, len(lines)):
                if 'Nummer' in lines[i] and 'Artikel' in lines[i]:
                    header_line = i
                    break
            
            if header_line is None:
                self.stdout.write(
                    self.style.ERROR('Could not find header line in GN X-Series Extra Articles CSV')
                )
                return 0
            
            # Read from the line after the header
            reader = csv.DictReader(lines[header_line:])
            for row in reader:
                try:
                    artikelnummer = row.get('Nummer', '').strip()
                    artikel = row.get('Artikel', '').strip()
                    
                    if not artikelnummer or not artikel:
                        continue
                    
                    # Skip header rows or invalid entries
                    if not artikelnummer.isdigit():
                        continue
                    
                    # Parse the Artikel column to extract diameter and position
                    # Pattern: "GN X - ZUB - Verteiler - Stütze - Oben/Unten - [diameter]"
                    # Handle both "Oben" and "Unten" (some files use "Unter" but this CSV uses "Unten")
                    match = re.search(r'Stütze\s*-\s*(Oben|Unten|Unter)\s*-\s*(\d+)', artikel, re.IGNORECASE)
                    if not match:
                        self.stdout.write(
                            self.style.WARNING(f'Could not parse Artikel for {artikelnummer}: {artikel}')
                        )
                        continue
                    
                    position = match.group(1).strip()
                    diameter = match.group(2).strip()
                    
                    # Normalize position: "Unten" -> "Unter" for consistency
                    if position.lower() == 'unten':
                        position = 'Unter'
                    elif position.lower() == 'oben':
                        position = 'Oben'
                    
                    # Create or update the entry
                    HVBStuetze.objects.update_or_create(
                        hvb_durchmesser=diameter,
                        position=position,
                        defaults={
                            'artikelnummer': artikelnummer,
                            'artikelbezeichnung': artikel
                        }
                    )
                    count += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'Error importing GN X Extra Article {row.get("Nummer", "unknown")}: {e}')
                    )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully imported {count} GN X-Series Extra Articles (HVB Stütze)')
        )
        
        return count