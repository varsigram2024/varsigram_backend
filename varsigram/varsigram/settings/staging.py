import os
from .base import *

DEBUG = False

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY') # Must be set as an environment variable in production

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',') # Must be set in production env

# Database configuration for production (PostgreSQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get("DB_NAME"),
        'USER': os.environ.get("DB_USER"),
        'PASSWORD': os.environ.get("DB_PASSWORD"),
        'HOST': os.environ.get("DB_HOST", "localhost"), # Consider using 'localhost' if DB is on same server or its internal IP
        'PORT': os.environ.get("DB_PORT", "5432"), # Default for PostgreSQL
        'ATOMIC_REQUESTS': True,
        'OPTIONS': {
            'options': '-c search_path=django,public' # Keep your specific search path
        }
    }
}

# Always use HTTPS in production
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000 # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Email Configuration for Production
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
# Ensure these are True in production for secure email
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False # If TLS is true, SSL is typically false. They are often mutually exclusive.

# CORS for production: Only allow from your actual frontend domain
CORS_ALLOWED_ORIGINS = os.environ.get('FRONTEND_URL', '').split(',') # Ensures it uses the actual env var

ENVIRONMENT = 'staging'
# Firebase settings for production (if used)
# FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROD_PROJECT_ID')
# FIREBASE_STORAGE_BUCKET = os.environ.get('FIREBASE_PROD_STORAGE_BUCKET')

# Celery for production (using RabbitMQ/Redis for production)
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') # Can be db or another broker

# Logging in production
# You might want to adjust handlers here, e.g., send errors to Sentry/email
LOGGING['handlers']['console']['level'] = 'INFO'
LOGGING['loggers']['django']['level'] = 'INFO'
LOGGING['loggers']['django.request']['handlers'] = ['file_error'] # Keep error file handler