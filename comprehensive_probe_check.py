#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bom_configurator.settings')
django.setup()

from configurator.models import Sondengroesse, Schacht, HVB

print("=== COMPREHENSIVE PROBE DATA CHECK ===")

# Check what's in the database
print("\n1. All probe combinations in database:")
probes = Sondengroesse.objects.all().order_by('schachttyp', 'hvb', 'durchmesser_sonde')
for p in probes:
    print(f"   {p.schachttyp:20} | HVB: {p.hvb:>3} | Durchmesser: {p.durchmesser_sonde}mm")

print(f"\n2. Total probes: {probes.count()}")

# Check what dropdowns should show
print("\n3. Available Schachttyp values in dropdown:")
schacht_values = Schacht.objects.all().order_by('schachttyp')
for s in schacht_values:
    print(f"   '{s.schachttyp}'")

print("\n4. Available HVB values in dropdown:")
hvb_values = HVB.objects.all().order_by('hauptverteilerbalken')
for h in hvb_values:
    print(f"   '{h.hauptverteilerbalken}'")

# Test specific combinations that should work
print("\n5. Testing combinations that SHOULD work:")
test_combinations = [
    ('GN R Kompakt', '63'),
    ('GN R Nano', '63'),
    ('GN X1', '75'),
    ('GN X1', '63'),
    ('GN X2', '140'),
    ('GN X3', '125'),
]

for schacht, hvb in test_combinations:
    matches = Sondengroesse.objects.filter(schachttyp=schacht, hvb=hvb)
    print(f"   '{schacht}' + '{hvb}': {matches.count()} probes")
    for match in matches:
        print(f"      -> {match.durchmesser_sonde}mm")

print("\n6. Checking for any string encoding issues:")
sample = Sondengroesse.objects.first()
if sample:
    print(f"   Sample schachttyp: '{sample.schachttyp}'")
    print(f"   Sample schachttyp bytes: {sample.schachttyp.encode('utf-8')}")
    print(f"   Sample hvb: '{sample.hvb}'")
    print(f"   Sample hvb bytes: {sample.hvb.encode('utf-8')}")

print("\n7. Testing exact string matching:")
test_schacht = 'GN R Kompakt'
test_hvb = '63'
exact_match = Sondengroesse.objects.filter(
    schachttyp__exact=test_schacht,
    hvb__exact=test_hvb
)
print(f"   Exact match '{test_schacht}' + '{test_hvb}': {exact_match.count()} probes")

# Show all unique schachttyp + hvb combinations
print("\n8. All unique schachttyp + hvb combinations:")
combinations = Sondengroesse.objects.values('schachttyp', 'hvb').distinct().order_by('schachttyp', 'hvb')
for combo in combinations:
    count = Sondengroesse.objects.filter(schachttyp=combo['schachttyp'], hvb=combo['hvb']).count()
    print(f"   '{combo['schachttyp']}' + '{combo['hvb']}' = {count} probe(s)")
