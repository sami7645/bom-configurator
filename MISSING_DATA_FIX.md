# Missing Sonden Diameters - Fix Report

## Issue Identified

The Sonden-Durchmesser dropdown was showing only 1 option (32mm) when it should show multiple options (25mm, 32mm, 40mm, 50mm, 63mm) for certain Schachttyp + HVB combinations.

## Root Cause

1. **Incomplete CSV Data**: The `Sondengroesse - Sondenlaenge.csv` file only contains 7 rows with limited combinations
2. **Overly Restrictive Query**: The query required exact match for both Schachttyp AND HVB, so if a combination didn't exist in the database, those diameters wouldn't appear

## Fix Applied

**File**: `configurator/views.py` (lines 119-155)

**New Logic**:
- Shows ALL available diameters for the selected Schachttyp
- For each diameter, prioritizes exact HVB match
- Falls back to any available entry for that Schachttyp + diameter if exact HVB match doesn't exist
- This ensures users see all possible diameters even if not all HVB combinations are in the database

**Before**:
```python
# Only showed diameters with exact Schachttyp + HVB match
sonden_options = Sondengroesse.objects.filter(
    schachttyp__iexact=schachttyp,
    hvb__iexact=hvb_size
)
```

**After**:
```python
# Get all diameters for schachttyp, prefer exact HVB match but include any available
for diameter in all_diameters_for_schachttyp:
    # Try exact match first
    exact_match = Sondengroesse.objects.filter(
        schachttyp__iexact=schachttyp,
        hvb__iexact=hvb_size,
        durchmesser_sonde=diameter
    ).first()
    
    if exact_match:
        # Use exact match
    else:
        # Use any available entry for this schachttyp + diameter
```

## Testing

**Test Case**: GN 1 + HVB 63mm
- **Before Fix**: Only showed 32mm (only entry in CSV)
- **After Fix**: Shows all diameters available for GN 1 (32mm, 40mm, etc. if they exist in DB)

**Note**: If diameters like 25mm, 50mm, 63mm don't appear, it means they don't exist in the database for that Schachttyp. They need to be added to the CSV file and imported.

## Next Steps

To get ALL expected diameters (25mm, 32mm, 40mm, 50mm, 63mm) for all Schachttyp combinations:

1. **Update CSV File**: Add missing combinations to `Sondengroesse - Sondenlaenge.csv`
2. **Re-import Data**: Run `python manage.py import_csv_data --file "Sondengroesse - Sondenlaenge.csv"`
3. **Verify**: Check dropdown shows all expected diameters

## Current Status

✅ **Query Logic Fixed** - Now shows all available diameters for Schachttyp
⚠️ **Data Completeness** - Some diameter combinations may still be missing from database

The fix ensures maximum visibility of available options, but complete data requires updating the CSV file with all required combinations.

