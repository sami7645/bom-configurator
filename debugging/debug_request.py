#!/usr/bin/env python
import os
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bom_configurator.settings')
django.setup()

from configurator.models import Sondengroesse, Schacht, HVB

print("=== DEBUGGING REQUEST MISMATCH ===")

# Check what values are actually in the dropdowns
print("\n1. Available Schacht values:")
schacht_values = Schacht.objects.all()
for s in schacht_values:
    print(f"  - '{s.schachttyp}' (ID: {s.id})")

print("\n2. Available HVB values:")
hvb_values = HVB.objects.all()
for h in hvb_values:
    print(f"  - '{h.hauptverteilerbalken}' (ID: {h.id})")

print("\n3. Probe data - what we're filtering against:")
probes = Sondengroesse.objects.all()[:10]
for p in probes:
    print(f"  - Schachttyp: '{p.schachttyp}' | HVB: '{p.hvb}' | Durchmesser: {p.durchmesser_sonde}mm")

print("\n4. Testing exact matches:")
# Test what the frontend is likely sending
test_cases = [
    ('GN R Kompakt', '63'),
    ('GN X1', '75'),
    ('GN R Nano', '63'),
]

for schacht, hvb in test_cases:
    matches = Sondengroesse.objects.filter(schachttyp=schacht, hvb=hvb)
    print(f"  '{schacht}' + '{hvb}': {matches.count()} matches")
    for match in matches:
        print(f"    -> {match.durchmesser_sonde}mm - {match.artikelbezeichnung}")

print("\n5. Check for whitespace/encoding issues:")
# Check for hidden characters
first_probe = Sondengroesse.objects.first()
if first_probe:
    print(f"First probe schachttyp repr: {repr(first_probe.schachttyp)}")
    print(f"First probe hvb repr: {repr(first_probe.hvb)}")
    print(f"Length of schachttyp: {len(first_probe.schachttyp)}")
    print(f"Length of hvb: {len(first_probe.hvb)}")

#!/usr/bin/env python
import os
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bom_configurator.settings')
django.setup()

from configurator.models import Sondengroesse, Schacht, HVB

print("=== DEBUGGING REQUEST MISMATCH ===")

# Check what values are actually in the dropdowns
print("\n1. Available Schacht values:")
schacht_values = Schacht.objects.all()
for s in schacht_values:
    print(f"  - '{s.schachttyp}' (ID: {s.id})")

print("\n2. Available HVB values:")
hvb_values = HVB.objects.all()
for h in hvb_values:
    print(f"  - '{h.hauptverteilerbalken}' (ID: {h.id})")

print("\n3. Probe data - what we're filtering against:")
probes = Sondengroesse.objects.all()[:10]
for p in probes:
    print(f"  - Schachttyp: '{p.schachttyp}' | HVB: '{p.hvb}' | Durchmesser: {p.durchmesser_sonde}mm")

print("\n4. Testing exact matches:")
# Test what the frontend is likely sending
test_cases = [
    ('GN R Kompakt', '63'),
    ('GN X1', '75'),
    ('GN R Nano', '63'),
]

for schacht, hvb in test_cases:
    matches = Sondengroesse.objects.filter(schachttyp=schacht, hvb=hvb)
    print(f"  '{schacht}' + '{hvb}': {matches.count()} matches")
    for match in matches:
        print(f"    -> {match.durchmesser_sonde}mm - {match.artikelbezeichnung}")

print("\n5. Check for whitespace/encoding issues:")
# Check for hidden characters
first_probe = Sondengroesse.objects.first()
if first_probe:
    print(f"First probe schachttyp repr: {repr(first_probe.schachttyp)}")
    print(f"First probe hvb repr: {repr(first_probe.hvb)}")
    print(f"Length of schachttyp: {len(first_probe.schachttyp)}")
    print(f"Length of hvb: {len(first_probe.hvb)}")

