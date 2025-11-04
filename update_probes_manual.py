#!/usr/bin/env python
"""
Manual script to add missing probe combinations
Run this if Railway deployment doesn't automatically update the probes
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bom_configurator.settings_production')
django.setup()

from configurator.models import Sondengroesse

def add_missing_probes():
    print("🔧 Adding missing probe combinations...")
    
    # Comprehensive probe data for all combinations
    additional_probes = [
        # GN X1 combinations
        {'durchmesser_sonde': '32', 'artikelnummer': '2000488', 'artikelbezeichnung': 'Rohr - PE 100-RC - 32', 'schachttyp': 'GN X1', 'hvb': '63', 'sondenanzahl_min': 5, 'sondenanzahl_max': 20, 'vorlauf_laenge': 0.280, 'ruecklauf_laenge': 0.365},
        {'durchmesser_sonde': '40', 'artikelnummer': '2000489', 'artikelbezeichnung': 'Rohr - PE 100-RC - 40', 'schachttyp': 'GN X1', 'hvb': '75', 'sondenanzahl_min': 5, 'sondenanzahl_max': 25, 'vorlauf_laenge': 0.280, 'ruecklauf_laenge': 0.365},
        {'durchmesser_sonde': '50', 'artikelnummer': '2000490', 'artikelbezeichnung': 'Rohr - PE 100-RC - 50', 'schachttyp': 'GN X1', 'hvb': '90', 'sondenanzahl_min': 5, 'sondenanzahl_max': 30, 'vorlauf_laenge': 0.280, 'ruecklauf_laenge': 0.365},
        
        # GN X3 combinations
        {'durchmesser_sonde': '32', 'artikelnummer': '2000488', 'artikelbezeichnung': 'Rohr - PE 100-RC - 32', 'schachttyp': 'GN X3', 'hvb': '110', 'sondenanzahl_min': 10, 'sondenanzahl_max': 50, 'vorlauf_laenge': 0.280, 'ruecklauf_laenge': 0.365},
        {'durchmesser_sonde': '40', 'artikelnummer': '2000489', 'artikelbezeichnung': 'Rohr - PE 100-RC - 40', 'schachttyp': 'GN X3', 'hvb': '125', 'sondenanzahl_min': 10, 'sondenanzahl_max': 60, 'vorlauf_laenge': 0.280, 'ruecklauf_laenge': 0.365},
        {'durchmesser_sonde': '50', 'artikelnummer': '2000490', 'artikelbezeichnung': 'Rohr - PE 100-RC - 50', 'schachttyp': 'GN X3', 'hvb': '140', 'sondenanzahl_min': 10, 'sondenanzahl_max': 70, 'vorlauf_laenge': 0.280, 'ruecklauf_laenge': 0.365},
        
        # GN X4 combinations
        {'durchmesser_sonde': '40', 'artikelnummer': '2000489', 'artikelbezeichnung': 'Rohr - PE 100-RC - 40', 'schachttyp': 'GN X4', 'hvb': '160', 'sondenanzahl_min': 15, 'sondenanzahl_max': 80, 'vorlauf_laenge': 0.280, 'ruecklauf_laenge': 0.365},
        {'durchmesser_sonde': '50', 'artikelnummer': '2000490', 'artikelbezeichnung': 'Rohr - PE 100-RC - 50', 'schachttyp': 'GN X4', 'hvb': '180', 'sondenanzahl_min': 15, 'sondenanzahl_max': 100, 'vorlauf_laenge': 0.280, 'ruecklauf_laenge': 0.365},
        
        # GN 2 combinations
        {'durchmesser_sonde': '32', 'artikelnummer': '2000488', 'artikelbezeichnung': 'Rohr - PE 100-RC - 32', 'schachttyp': 'GN 2', 'hvb': '63', 'sondenanzahl_min': 5, 'sondenanzahl_max': 15, 'vorlauf_laenge': 0.265, 'ruecklauf_laenge': 0.365},
        {'durchmesser_sonde': '40', 'artikelnummer': '2000489', 'artikelbezeichnung': 'Rohr - PE 100-RC - 40', 'schachttyp': 'GN 2', 'hvb': '75', 'sondenanzahl_min': 5, 'sondenanzahl_max': 20, 'vorlauf_laenge': 0.265, 'ruecklauf_laenge': 0.365},
        
        # GN R Medium combinations
        {'durchmesser_sonde': '32', 'artikelnummer': '2000488', 'artikelbezeichnung': 'Rohr - PE 100-RC - 32', 'schachttyp': 'GN R Medium', 'hvb': '63', 'sondenanzahl_min': 3, 'sondenanzahl_max': 8, 'vorlauf_laenge': 0.200, 'ruecklauf_laenge': 0.300},
        {'durchmesser_sonde': '40', 'artikelnummer': '2000489', 'artikelbezeichnung': 'Rohr - PE 100-RC - 40', 'schachttyp': 'GN R Medium', 'hvb': '75', 'sondenanzahl_min': 3, 'sondenanzahl_max': 10, 'vorlauf_laenge': 0.200, 'ruecklauf_laenge': 0.300},
        
        # GN R Mini combinations
        {'durchmesser_sonde': '32', 'artikelnummer': '2000488', 'artikelbezeichnung': 'Rohr - PE 100-RC - 32', 'schachttyp': 'GN R Mini', 'hvb': '63', 'sondenanzahl_min': 2, 'sondenanzahl_max': 5, 'vorlauf_laenge': 0.150, 'ruecklauf_laenge': 0.250},
        
        # More GN 1 combinations
        {'durchmesser_sonde': '40', 'artikelnummer': '2000489', 'artikelbezeichnung': 'Rohr - PE 100-RC - 40', 'schachttyp': 'GN 1', 'hvb': '75', 'sondenanzahl_min': 8, 'sondenanzahl_max': 15, 'vorlauf_laenge': 0.265, 'ruecklauf_laenge': 0.365},
    ]

    count = 0
    for probe_data in additional_probes:
        # Check if combination already exists
        existing = Sondengroesse.objects.filter(
            durchmesser_sonde=probe_data['durchmesser_sonde'],
            schachttyp=probe_data['schachttyp'],
            hvb=probe_data['hvb']
        ).first()
        
        if not existing:
            Sondengroesse.objects.create(**probe_data)
            count += 1
            print(f'✅ Added: {probe_data["schachttyp"]} + {probe_data["hvb"]}mm HVB + {probe_data["durchmesser_sonde"]}mm probe')

    print(f'\n🎉 Successfully added {count} new probe combinations!')
    print(f'📊 Total probe records now: {Sondengroesse.objects.count()}')
    
    return count

if __name__ == '__main__':
    try:
        count = add_missing_probes()
        if count > 0:
            print(f'\n✅ Database updated successfully! Added {count} probe combinations.')
        else:
            print(f'\n✅ All probe combinations already exist!')
        print('🚀 Your Sonden-Durchmesser dropdown should now work!')
    except Exception as e:
        print(f'\n❌ Error: {e}')
        sys.exit(1)
