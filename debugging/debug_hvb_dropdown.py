#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bom_configurator.settings')
django.setup()

from configurator.models import HVB

print("=== DEBUGGING HVB DROPDOWN ===")

# Check what the HVB dropdown should contain
hvb_values = HVB.objects.all().order_by('hauptverteilerbalken')

print("HVB dropdown HTML that should be generated:")
print('<select class="form-select" id="hvbSize" name="hvb_size" required>')
print('    <option value="">Bitte wählen...</option>')

for hvb in hvb_values:
    print(f'    <option value="{hvb.hauptverteilerbalken}">{hvb.hauptverteilerbalken}mm</option>')

print('</select>')

print(f"\nTotal HVB options: {hvb_values.count()}")

print("\nHVB values in order:")
for i, hvb in enumerate(hvb_values):
    print(f"  {i+1}. Value: '{hvb.hauptverteilerbalken}' | Display: '{hvb.hauptverteilerbalken}mm'")

print("\nCheck if '63' is in the list:")
hvb_63 = HVB.objects.filter(hauptverteilerbalken='63').first()
if hvb_63:
    print(f"  Found: '{hvb_63.hauptverteilerbalken}' (ID: {hvb_63.id})")
else:
    print("  NOT FOUND!")

print("\nCheck if '280' is in the list:")
hvb_280 = HVB.objects.filter(hauptverteilerbalken='280').first()
if hvb_280:
    print(f"  Found: '{hvb_280.hauptverteilerbalken}' (ID: {hvb_280.id})")
else:
    print("  NOT FOUND!")

print("\nAll HVB values as list:")
all_hvb_values = list(hvb_values.values_list('hauptverteilerbalken', flat=True))
print(f"  {all_hvb_values}")

print(f"\nIs '63' in the list? {'63' in all_hvb_values}")
print(f"Is '280' in the list? {'280' in all_hvb_values}")

#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bom_configurator.settings')
django.setup()

from configurator.models import HVB

print("=== DEBUGGING HVB DROPDOWN ===")

# Check what the HVB dropdown should contain
hvb_values = HVB.objects.all().order_by('hauptverteilerbalken')

print("HVB dropdown HTML that should be generated:")
print('<select class="form-select" id="hvbSize" name="hvb_size" required>')
print('    <option value="">Bitte wählen...</option>')

for hvb in hvb_values:
    print(f'    <option value="{hvb.hauptverteilerbalken}">{hvb.hauptverteilerbalken}mm</option>')

print('</select>')

print(f"\nTotal HVB options: {hvb_values.count()}")

print("\nHVB values in order:")
for i, hvb in enumerate(hvb_values):
    print(f"  {i+1}. Value: '{hvb.hauptverteilerbalken}' | Display: '{hvb.hauptverteilerbalken}mm'")

print("\nCheck if '63' is in the list:")
hvb_63 = HVB.objects.filter(hauptverteilerbalken='63').first()
if hvb_63:
    print(f"  Found: '{hvb_63.hauptverteilerbalken}' (ID: {hvb_63.id})")
else:
    print("  NOT FOUND!")

print("\nCheck if '280' is in the list:")
hvb_280 = HVB.objects.filter(hauptverteilerbalken='280').first()
if hvb_280:
    print(f"  Found: '{hvb_280.hauptverteilerbalken}' (ID: {hvb_280.id})")
else:
    print("  NOT FOUND!")

print("\nAll HVB values as list:")
all_hvb_values = list(hvb_values.values_list('hauptverteilerbalken', flat=True))
print(f"  {all_hvb_values}")

print(f"\nIs '63' in the list? {'63' in all_hvb_values}")
print(f"Is '280' in the list? {'280' in all_hvb_values}")

