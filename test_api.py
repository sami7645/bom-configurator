#!/usr/bin/env python
import os
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bom_configurator.settings')
django.setup()

from configurator.models import Sondengroesse

print("=== TESTING API LOGIC ===")

# Test the same logic as the API endpoint
test_cases = [
    {'schachttyp': 'GN R Kompakt', 'hvb_size': '63'},
    {'schachttyp': 'GN X1', 'hvb_size': '75'},
    {'schachttyp': 'GN X3', 'hvb_size': '125'},
]

for test_case in test_cases:
    schachttyp = test_case['schachttyp']
    hvb_size = test_case['hvb_size']
    
    print(f"\nTesting: {schachttyp} + {hvb_size}mm")
    
    sonden_options = Sondengroesse.objects.filter(
        schachttyp=schachttyp,
        hvb=hvb_size
    ).values(
        'durchmesser_sonde', 'sondenanzahl_min', 'sondenanzahl_max',
        'artikelnummer', 'artikelbezeichnung'
    ).distinct()
    
    options_list = list(sonden_options)
    print(f"Found {len(options_list)} options:")
    
    for option in options_list:
        print(f"  -> {option['durchmesser_sonde']}mm - {option['artikelbezeichnung']}")
    
    if len(options_list) == 0:
        # Debug: check what values are actually in the database
        all_schacht = Sondengroesse.objects.filter(schachttyp__icontains=schachttyp.split()[0]).values_list('schachttyp', flat=True).distinct()
        all_hvb = Sondengroesse.objects.filter(hvb=hvb_size).values_list('hvb', flat=True).distinct()
        print(f"  DEBUG: Similar Schachttyp values: {list(all_schacht)}")
        print(f"  DEBUG: HVB {hvb_size} exists: {list(all_hvb)}")

print("\n=== TESTING EXACT MATCHES ===")
# Check for exact string matches
exact_matches = Sondengroesse.objects.filter(schachttyp__exact='GN R Kompakt', hvb__exact='63')
print(f"Exact match 'GN R Kompakt' + '63': {exact_matches.count()} results")
for match in exact_matches:
    print(f"  -> {match.durchmesser_sonde}mm - '{match.schachttyp}' - '{match.hvb}'")
