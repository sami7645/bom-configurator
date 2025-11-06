# Production settings for deployment
from .settings import *
import os
import dj_database_url

# Override settings for production
DEBUG = False
ALLOWED_HOSTS = ['*']

# Add WhiteNoise middleware for static files
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Database for production
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Static files for production
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Security settings
SECURE_SSL_REDIRECT = False  # Set to True if using HTTPS
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# CSRF settings for Railway deployment
# Get Railway domain from environment variable or use default
RAILWAY_PUBLIC_DOMAIN = os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'web-production-d6edc.up.railway.app')

# CSRF_TRUSTED_ORIGINS must list specific domains (no wildcards)
CSRF_TRUSTED_ORIGINS = [
    f'https://{RAILWAY_PUBLIC_DOMAIN}',
]

# Add any additional Railway domains if needed
# Ensure any domain added includes scheme (Django 4+ requirement)
extra_origin = os.environ.get('RAILWAY_STATIC_URL')
if extra_origin:
    if not extra_origin.startswith('http://') and not extra_origin.startswith('https://'):
        extra_origin = f'https://{extra_origin}'
    CSRF_TRUSTED_ORIGINS.append(extra_origin)

# Also allow HTTP for local testing (remove in production)
if os.environ.get('RAILWAY_ENVIRONMENT') != 'production':
    CSRF_TRUSTED_ORIGINS.extend([
        'http://localhost:8000',
        'http://127.0.0.1:8000',
    ])

# CSRF cookie settings for HTTPS
CSRF_COOKIE_SECURE = True  # Only send CSRF cookie over HTTPS
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# Session cookie settings for HTTPS
SESSION_COOKIE_SECURE = True  # Only send session cookie over HTTPS
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'