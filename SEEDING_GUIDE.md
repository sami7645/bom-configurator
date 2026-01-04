# 🌱 Database Seeding Guide

This project automatically seeds the database with CSV data after migrations.

## ✅ Automatic Seeding

### How It Works

1. **Post-Migration Signal**: After any migration runs, the app automatically checks if the database is empty and seeds it if needed.

2. **Smart Detection**: Seeding only runs if:
   - The `configurator_schacht` table is empty (no data exists)
   - This prevents re-seeding on every migration

3. **What Gets Seeded**:
   - All CSV files from `excel_sheets_extracted/` directory
   - GN X chamber articles (hardcoded data)
   - Missing probe combinations

## 🚀 Manual Seeding Commands

### Run All Seeding
```bash
python manage.py import_csv_data --force
python manage.py add_missing_probes
```

### Combined Migration + Seeding
```bash
python manage.py migrate_and_seed
```

This command:
- Runs all migrations
- Automatically seeds the database
- Use `--no-seed` to skip seeding

## 📋 Seeding Commands

### 1. `import_csv_data`
Imports all CSV files:
- `Schacht.csv`
- `HVB.csv`
- `Sondengroesse - Sondenlaenge.csv`
- `Sondenabstaende.csv`
- `Kugelhaehne.csv`
- `DFM.csv`
- `Entlueftung.csv`
- `Sondenverschlusskappe.csv`
- `Stumpfschweiss-Endkappen.csv`
- `WP-Verschlusskappen.csv`
- `WPA.csv`
- `Verrohrung.csv`
- `Schachtgrenze.csv`
- `Schachtkompatibilitaet.csv`
- GN X chamber articles (hardcoded)
- Missing probe combinations

**Options:**
- `--force`: Force reimport even if file hasn't changed
- `--file FILENAME`: Import specific CSV file only

### 2. `add_missing_probes`
Adds missing probe combinations to ensure dropdowns work correctly.

### 3. `migrate_and_seed`
Combined command that runs migrations and then seeds.

**Options:**
- `--no-seed`: Skip seeding after migration
- `--fake`: Mark migrations as run without actually running them
- `--fake-initial`: Detect if tables already exist and fake-apply initial migrations

## 🔄 Deployment

### Railway/Render (Procfile)
The `Procfile` uses `migrate_and_seed` in the release phase:
```
release: python manage.py migrate_and_seed --settings=bom_configurator.settings_production && python manage.py collectstatic --noinput --settings=bom_configurator.settings_production
```

This ensures:
1. Migrations run
2. Database is seeded automatically
3. Static files are collected

### Manual Deployment
If deploying manually, run:
```bash
python manage.py migrate_and_seed
python manage.py collectstatic --noinput
```

## 🛠️ Development

### First Time Setup
```bash
# Create venv and install
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
pip install -r requirements_local.txt

# Run migrations (seeding happens automatically)
python manage.py migrate
```

### Re-seeding
If you need to re-seed:
```bash
python manage.py import_csv_data --force
python manage.py add_missing_probes
```

Or use the combined command:
```bash
python manage.py migrate_and_seed
```

## 📝 Notes

- **Automatic seeding** only runs if the database is empty
- **CSV files** are located in `excel_sheets_extracted/` directory
- **Seeding is idempotent** - running multiple times is safe
- **Use `--force`** to reimport even if files haven't changed

## 🔍 Troubleshooting

### Seeding Not Running?
1. Check if data already exists: `python manage.py shell` → `from configurator.models import Schacht; print(Schacht.objects.count())`
2. If data exists, use `--force` flag: `python manage.py import_csv_data --force`
3. Check CSV files exist in `excel_sheets_extracted/` directory

### CSV Import Errors?
- Check file encoding (UTF-8, UTF-8-sig, Latin1, CP1252 are supported)
- Verify CSV file format matches expected structure
- Check file paths in `settings.CSV_FILES_DIR`

