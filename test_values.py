#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bom_configurator.settings')
django.setup()

from configurator.models import Schacht, HVB, Sondengroesse

print("=== CHECKING DROPDOWN VALUES ===")

print("\n1. Schacht dropdown values (what frontend sends):")
schacht_values = Schacht.objects.all().order_by('schachttyp')
for s in schacht_values:
    print(f"  Value: '{s.schachttyp}' | Display: '{s.schachttyp}'")

print("\n2. HVB dropdown values (what frontend sends):")
hvb_values = HVB.objects.all().order_by('hauptverteilerbalken')
for h in hvb_values:
    print(f"  Value: '{h.hauptverteilerbalken}' | Display: '{h.hauptverteilerbalken}mm'")

print("\n3. What Sondengroesse expects:")
probe_combinations = Sondengroesse.objects.values('schachttyp', 'hvb').distinct().order_by('schachttyp', 'hvb')
for combo in probe_combinations:
    print(f"  Schachttyp: '{combo['schachttyp']}' | HVB: '{combo['hvb']}'")

print("\n4. Testing specific matches:")
# Test the exact values that should work
test_schacht = 'GN R Kompakt'
test_hvb = '63'

# Check if these exist in the dropdown sources
schacht_exists = Schacht.objects.filter(schachttyp=test_schacht).exists()
hvb_exists = HVB.objects.filter(hauptverteilerbalken=test_hvb).exists()

print(f"  '{test_schacht}' exists in Schacht table: {schacht_exists}")
print(f"  '{test_hvb}' exists in HVB table: {hvb_exists}")

# Check if this combination exists in Sondengroesse
probe_exists = Sondengroesse.objects.filter(schachttyp=test_schacht, hvb=test_hvb).exists()
probe_count = Sondengroesse.objects.filter(schachttyp=test_schacht, hvb=test_hvb).count()

print(f"  '{test_schacht}' + '{test_hvb}' exists in Sondengroesse: {probe_exists}")
print(f"  Number of probes for this combination: {probe_count}")

if probe_count > 0:
    probes = Sondengroesse.objects.filter(schachttyp=test_schacht, hvb=test_hvb)
    for probe in probes:
        print(f"    -> {probe.durchmesser_sonde}mm - {probe.artikelbezeichnung}")
