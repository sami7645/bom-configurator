# Testing Guide: Mother and Child Article Functionality

## Overview
This guide explains how to test the mother/child article detection system that checks if configurations already exist in the database.

## Test Scenario 1: Create a Mother Article Configuration

### Step 1: Create First Configuration (Mother Article)
1. Go to the configurator: `http://127.0.0.1:8006/configurator/`
2. Fill in Step 1:
   - **Konfigurationsname**: `Test Mother Article`
   - **Schachttyp**: `GN 1`
   - **HVB-Größe**: `110mm`
   - **Anschlussart**: `beidseitig`
3. Fill in Step 2:
   - **Sonden-Durchmesser**: Select any (e.g., `40mm`)
   - **Anzahl Sonden**: `10`
   - **Sondenabstand**: `100mm (Standard)`
   - **Bauform**: `U-Form`
4. Fill in Step 3 (optional components):
   - **Kugelhahn-Typ**: `DN 25 / DA 32` (optional)
   - **DFM-Typ**: `K-DFM 8-28` (optional)
5. Go to Step 4 (Configuration Check):
   - You should see: **"Neue Konfiguration - Artikelnummer muss erstellt werden"**
   - Enter a **full article number**: `1000089-001` (the system will automatically extract mother `1000089` and child `001`)
   - Click **"BOM GENERIEREN"**
6. Complete Step 5 and save the configuration

### Step 2: Verify Mother Article in Database
You can check via Django Admin:
1. Go to: `http://127.0.0.1:8006/admin/configurator/bomconfiguration/`
2. Find your configuration "Test Mother Article"
3. Check that:
   - `mother_article_number` = `1000089`
   - `child_article_number` = `001` (or similar)
   - `full_article_number` = `1000089-001`

---

## Test Scenario 2: Create Child Article (Same Base, Different Details)

### Step 1: Create Similar Configuration
1. Go to the configurator again
2. Fill in Step 1 with **SAME base parameters**:
   - **Konfigurationsname**: `Test Child Article`
   - **Schachttyp**: `GN 1` (SAME as mother)
   - **HVB-Größe**: `110mm` (SAME as mother)
   - **Anschlussart**: `beidseitig` (SAME as mother)
3. Fill in Step 2 with **SAME base parameters**:
   - **Sonden-Durchmesser**: `40mm` (SAME as mother)
   - **Anzahl Sonden**: `12` (DIFFERENT - this makes it a child)
   - **Sondenabstand**: `100mm` (SAME)
   - **Bauform**: `U-Form` (SAME)
4. Fill in Step 3 (can be different):
   - **Kugelhahn-Typ**: `DN 25 / DA 32` (can be same or different)
   - **DFM-Typ**: `K-DFM 8-28` (can be same or different)
5. Go to Step 4 (Configuration Check):
   - **Expected Result**: You should see:
     - **"Mutterartikel gefunden"** (Mother article found)
     - **Message**: `Mutterartikel "1000089" existiert bereits, aber es gibt keine Kindartikelnummer zu dieser Konfiguration.`
     - **Kindartikelnummer field** should be pre-filled with: `1000089-002` (next child number)
     - The system will automatically extract mother `1000089` and child `002` from this
6. Click **"BOM GENERIEREN"** and complete

### Step 2: Verify Child Article
1. Go to Django Admin
2. Find "Test Child Article"
3. Check that:
   - `mother_article_number` = `1000089` (same as mother)
   - `child_article_number` = `002` (next child number)
   - `full_article_number` = `1000089-002`

---

## Test Scenario 3: Exact Configuration Already Exists

### Step 1: Try to Create Exact Duplicate
1. Go to the configurator
2. Fill in **EXACTLY the same** as the first configuration:
   - **Schachttyp**: `GN 1`
   - **HVB-Größe**: `110mm`
   - **Sonden-Durchmesser**: `40mm`
   - **Anzahl Sonden**: `10` (SAME as mother)
   - **Sondenabstand**: `100mm`
   - **Anschlussart**: `beidseitig`
   - **Bauform**: `U-Form`
   - **Kugelhahn-Typ**: `DN 25 / DA 32` (SAME)
   - **DFM-Typ**: `K-DFM 8-28` (SAME)
3. Go to Step 4:
   - **Expected Result**: You should see:
     - **"Konfiguration bereits vorhanden"** (Configuration already exists)
     - **Message**: `Diese Konfiguration existiert bereits mit Artikelnummer: 1000089-001`
     - **No input field** - it should show the existing article number

---

## Test Scenario 4: Multiple Child Articles

### Step 1: Create Multiple Children
1. Create 2-3 more configurations with:
   - **Same base**: `GN 1`, `110mm`, `40mm`
   - **Different details**: Different `sondenanzahl`, `kugelhahn_type`, etc.
2. Each should get the next child number:
   - First child: `1000089-002`
   - Second child: `1000089-003`
   - Third child: `1000089-004`

### Step 2: Verify Sequential Numbering
1. Check in Django Admin that child numbers are sequential
2. Try creating another child - it should suggest `1000089-005`

---

## Quick Test via Django Admin

### Manual Database Check:
1. Go to: `http://127.0.0.1:8006/admin/configurator/bomconfiguration/`
2. You can manually edit configurations to set:
   - `mother_article_number` = `1000089`
   - `child_article_number` = `001`
   - `full_article_number` = `1000089-001`
3. Then test the configurator to see if it detects it

---

## Expected Behavior Summary

| Scenario | Base Match | Details Match | Result |
|----------|-----------|-------------|--------|
| Exact duplicate | ✅ | ✅ | Shows: "Configuration already exists with article number: 1000089-001" |
| Same base, different details | ✅ | ❌ | Shows: "Mother article '1000089' exists, but no child article for this configuration" |
| Completely new | ❌ | ❌ | Shows: "New configuration - article number must be created" |

---

## Troubleshooting

### If mother article is not detected:
1. Check that the base parameters match exactly:
   - `schachttyp` must be identical
   - `hvb_size` must be identical
   - `sonden_durchmesser` must be identical
2. Check in Django Admin that the first configuration has `mother_article_number` set

### If child number is wrong:
1. Check existing children in database
2. The system finds the highest child number and adds 1
3. If you manually set child numbers, make sure they're sequential

### To reset test data:
1. Go to Django Admin
2. Delete test configurations
3. Start fresh

---

## Database Query to Check Mother/Child Relationships

You can run this in Django shell (`python manage.py shell`):

```python
from configurator.models import BOMConfiguration

# Find all mother articles
mothers = BOMConfiguration.objects.exclude(mother_article_number__isnull=True).exclude(mother_article_number='')
for m in mothers:
    print(f"Mother: {m.mother_article_number}")
    children = BOMConfiguration.objects.filter(mother_article_number=m.mother_article_number)
    for c in children:
        print(f"  Child: {c.child_article_number} - Full: {c.full_article_number}")
```

