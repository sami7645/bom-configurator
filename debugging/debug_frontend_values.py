#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bom_configurator.settings')
django.setup()

from configurator.models import Schacht, HVB, Sondengroesse

print("=== DEBUGGING FRONTEND VALUES ===")

# Check what the frontend dropdowns should contain
print("\n1. What Schachttyp dropdown should show:")
schacht_values = Schacht.objects.all().order_by('schachttyp')
for s in schacht_values:
    print(f"  <option value=\"{s.schachttyp}\">{s.schachttyp}</option>")

print("\n2. What HVB dropdown should show:")
hvb_values = HVB.objects.all().order_by('hauptverteilerbalken')
for h in hvb_values:
    print(f"  <option value=\"{h.hauptverteilerbalken}\">{h.hauptverteilerbalken}mm</option>")

print("\n3. Test if 'GN R Kompakt' and '63' exist exactly as strings:")
test_schacht = 'GN R Kompakt'
test_hvb = '63'

# Check exact string matches
schacht_match = Schacht.objects.filter(schachttyp__exact=test_schacht).first()
hvb_match = HVB.objects.filter(hauptverteilerbalken__exact=test_hvb).first()

print(f"  Schacht '{test_schacht}' found: {schacht_match is not None}")
if schacht_match:
    print(f"    Exact value: '{schacht_match.schachttyp}'")
    print(f"    Length: {len(schacht_match.schachttyp)}")
    print(f"    Repr: {repr(schacht_match.schachttyp)}")

print(f"  HVB '{test_hvb}' found: {hvb_match is not None}")
if hvb_match:
    print(f"    Exact value: '{hvb_match.hauptverteilerbalken}'")
    print(f"    Length: {len(hvb_match.hauptverteilerbalken)}")
    print(f"    Repr: {repr(hvb_match.hauptverteilerbalken)}")

print("\n4. Test Sondengroesse filtering with these exact values:")
probes = Sondengroesse.objects.filter(schachttyp=test_schacht, hvb=test_hvb)
print(f"  Found {probes.count()} probes for '{test_schacht}' + '{test_hvb}'")

for probe in probes:
    print(f"    -> {probe.durchmesser_sonde}mm - {probe.artikelbezeichnung}")
    print(f"       Schachttyp: '{probe.schachttyp}' (len: {len(probe.schachttyp)})")
    print(f"       HVB: '{probe.hvb}' (len: {len(probe.hvb)})")

print("\n5. Check for any character encoding issues:")
if probes.exists():
    first_probe = probes.first()
    schacht_bytes = first_probe.schachttyp.encode('utf-8')
    hvb_bytes = first_probe.hvb.encode('utf-8')
    print(f"  Schachttyp UTF-8 bytes: {schacht_bytes}")
    print(f"  HVB UTF-8 bytes: {hvb_bytes}")

print("\n6. Show all unique combinations that DO exist:")
existing_combinations = Sondengroesse.objects.values('schachttyp', 'hvb').distinct().order_by('schachttyp', 'hvb')
print("  Existing combinations:")
for combo in existing_combinations:
    count = Sondengroesse.objects.filter(schachttyp=combo['schachttyp'], hvb=combo['hvb']).count()
    print(f"    '{combo['schachttyp']}' + '{combo['hvb']}' = {count} probes")

#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bom_configurator.settings')
django.setup()

from configurator.models import Schacht, HVB, Sondengroesse

print("=== DEBUGGING FRONTEND VALUES ===")

# Check what the frontend dropdowns should contain
print("\n1. What Schachttyp dropdown should show:")
schacht_values = Schacht.objects.all().order_by('schachttyp')
for s in schacht_values:
    print(f"  <option value=\"{s.schachttyp}\">{s.schachttyp}</option>")

print("\n2. What HVB dropdown should show:")
hvb_values = HVB.objects.all().order_by('hauptverteilerbalken')
for h in hvb_values:
    print(f"  <option value=\"{h.hauptverteilerbalken}\">{h.hauptverteilerbalken}mm</option>")

print("\n3. Test if 'GN R Kompakt' and '63' exist exactly as strings:")
test_schacht = 'GN R Kompakt'
test_hvb = '63'

# Check exact string matches
schacht_match = Schacht.objects.filter(schachttyp__exact=test_schacht).first()
hvb_match = HVB.objects.filter(hauptverteilerbalken__exact=test_hvb).first()

print(f"  Schacht '{test_schacht}' found: {schacht_match is not None}")
if schacht_match:
    print(f"    Exact value: '{schacht_match.schachttyp}'")
    print(f"    Length: {len(schacht_match.schachttyp)}")
    print(f"    Repr: {repr(schacht_match.schachttyp)}")

print(f"  HVB '{test_hvb}' found: {hvb_match is not None}")
if hvb_match:
    print(f"    Exact value: '{hvb_match.hauptverteilerbalken}'")
    print(f"    Length: {len(hvb_match.hauptverteilerbalken)}")
    print(f"    Repr: {repr(hvb_match.hauptverteilerbalken)}")

print("\n4. Test Sondengroesse filtering with these exact values:")
probes = Sondengroesse.objects.filter(schachttyp=test_schacht, hvb=test_hvb)
print(f"  Found {probes.count()} probes for '{test_schacht}' + '{test_hvb}'")

for probe in probes:
    print(f"    -> {probe.durchmesser_sonde}mm - {probe.artikelbezeichnung}")
    print(f"       Schachttyp: '{probe.schachttyp}' (len: {len(probe.schachttyp)})")
    print(f"       HVB: '{probe.hvb}' (len: {len(probe.hvb)})")

print("\n5. Check for any character encoding issues:")
if probes.exists():
    first_probe = probes.first()
    schacht_bytes = first_probe.schachttyp.encode('utf-8')
    hvb_bytes = first_probe.hvb.encode('utf-8')
    print(f"  Schachttyp UTF-8 bytes: {schacht_bytes}")
    print(f"  HVB UTF-8 bytes: {hvb_bytes}")

print("\n6. Show all unique combinations that DO exist:")
existing_combinations = Sondengroesse.objects.values('schachttyp', 'hvb').distinct().order_by('schachttyp', 'hvb')
print("  Existing combinations:")
for combo in existing_combinations:
    count = Sondengroesse.objects.filter(schachttyp=combo['schachttyp'], hvb=combo['hvb']).count()
    print(f"    '{combo['schachttyp']}' + '{combo['hvb']}' = {count} probes")

