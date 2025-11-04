@echo off
echo ========================================
echo    BOM Konfigurator - Deployment Setup
echo ========================================
echo.
echo This will prepare your project for deployment
echo.
echo Step 1: Installing deployment dependencies...
pip install -r requirements.txt
echo.
echo Step 2: Collecting static files...
python manage.py collectstatic --noinput
echo.
echo Step 3: Testing migrations...
python manage.py makemigrations
python manage.py migrate
echo.
echo Step 4: Importing CSV data...
python manage.py import_csv_data --force
echo.
echo ========================================
echo    READY FOR DEPLOYMENT!
echo ========================================
echo.
echo Next steps:
echo 1. Upload to GitHub (see DEPLOYMENT.md)
echo 2. Deploy on Railway/Render (see DEPLOYMENT.md)
echo 3. Share URL with client
echo.
echo Your project is now deployment-ready!
echo.
pause
