#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bom_configurator.settings')
django.setup()

from configurator.models import Sondengroesse

print("=== PROBE DATA CHECK ===")
total_probes = Sondengroesse.objects.count()
print(f"Total probes in database: {total_probes}")

if total_probes > 0:
    print("\nSample probes:")
    for p in Sondengroesse.objects.all()[:10]:
        print(f"  {p.durchmesser_sonde}mm - '{p.schachttyp}' - '{p.hvb}' - {p.artikelbezeichnung}")
    
    print("\n=== TESTING SPECIFIC COMBINATIONS ===")
    
    # Test GN R Kompakt + 63
    gnr_kompakt_63 = Sondengroesse.objects.filter(schachttyp='GN R Kompakt', hvb='63')
    print(f"GN R Kompakt + 63mm HVB: {gnr_kompakt_63.count()} probes")
    for p in gnr_kompakt_63:
        print(f"  -> {p.durchmesser_sonde}mm - {p.artikelbezeichnung}")
    
    # Test GN X1 + 75
    gnx1_75 = Sondengroesse.objects.filter(schachttyp='GN X1', hvb='75')
    print(f"GN X1 + 75mm HVB: {gnx1_75.count()} probes")
    for p in gnx1_75:
        print(f"  -> {p.durchmesser_sonde}mm - {p.artikelbezeichnung}")
    
    # Show all unique schachttyp values
    schacht_types = Sondengroesse.objects.values_list('schachttyp', flat=True).distinct()
    print(f"\nAll Schachttyp values: {list(schacht_types)}")
    
    # Show all unique hvb values
    hvb_values = Sondengroesse.objects.values_list('hvb', flat=True).distinct()
    print(f"All HVB values: {list(hvb_values)}")
    
else:
    print("No probe data found in database!")
