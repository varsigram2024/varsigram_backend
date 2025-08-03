from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
# Use a development-specific key or a placeholder for local dev
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-your-development-secret-key-here')

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Database for local development (Postgres)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get("DB_NAME", ""),
        'USER': os.environ.get("DB_USER", ""),
        'PASSWORD': os.environ.get("DB_PASSWORD", ""),
        'HOST': os.environ.get("DB_HOST", "localhost"),
        'PORT': os.environ.get("DB_PORT", ""),
        'ATOMIC_REQUESTS': True,
        'OPTIONS': {
            'options': '-c search_path=django,public'
        }

    }
}

# Example: If you have different CORS origins for local development
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000', # Your frontend dev server
    'http://127.0.0.1:3000',
]

# For local development, you might want to print emails to console
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')

# Celery for local development might use a local RabbitMQ or Redis
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'


# Firebase settings for local (if you use Firebase emulators)
# FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_DEV_PROJECT_ID', default=None)
# FIREBASE_STORAGE_BUCKET = os.environ.get('FIREBASE_DEV_STORAGE_BUCKET', default=None)

# Local Logging configuration (optional, can override base if needed)
# For example, you might want more verbose logging in development
LOGGING['handlers']['console']['level'] = 'DEBUG'
LOGGING['loggers']['django']['level'] = 'DEBUG'