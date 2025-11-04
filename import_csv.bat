@echo off
echo ========================================
echo    BOM Konfigurator - CSV Import
echo ========================================
echo.
echo Importiere CSV-Daten...
echo.
python manage.py import_csv_data --force
echo.
echo CSV-Import abgeschlossen!
echo.
pause
