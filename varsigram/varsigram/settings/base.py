import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# Load .env variables for local development.
# In production, environment variables will be set by the CI/CD system or server config.
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent # Adjusted path for settings directory


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework.authtoken',
    'django_filters',
    # 'social_django', # Uncomment if you enable it later

    #Local Apps
    'users',
    'chat',
    'corsheaders',
    'postMang',
    'django_celery_results',  # For storing task results in the database
    # 'postMang.apps.FirebaseConfig',  # Firebase configuration app - keep commented unless truly needed
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

SECURE_BROWSER_XSS_FILTER = True # Enable XSS Filter in browsers
X_FRAME_OPTIONS = 'DENY' # Prevent Clickjacking

# Google OAuth Config (ensure these are handled securely, probably in production.py via env vars)
# GOOGLE_OAUTH2_CLIENT_ID = os.environ.get('GOOGLE_OAUTH2_CLIENT_ID')
# GOOGLE_OAUTH2_CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH2_CLIENT_SECRET')
# GOOGLE_OAUTH2_PROJECT_ID = os.environ.get('GOOGLE_OAUTH2_PROJECT_ID')


ROOT_URLCONF = 'varsigram.urls' # Keep your main project name

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'varsigram.wsgi.application'
ASGI_APPLICATION = 'varsigram.asgi.application' # Keep your main project name

#FIREBASE SETTINGS (moved to production.py if used there)
# FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID', default=None)
# FIREBASE_STORAGE_BUCKET = os.environ.get('FIREBASE_STORAGE_BUCKET', default=None)


# Database (will be overridden in env-specific settings)
# For now, a placeholder or default for development if not overridden
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Rest Framework Settings
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ),
}

#JWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=10),  # Recommended: short lifetime for access tokens
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),   # Longer lifetime for refresh tokens
    'ROTATE_REFRESH_TOKENS': True,                  # Generates a new refresh token on refresh
    'BLACKLIST_AFTER_ROTATION': True,               # Invalidates old refresh token (requires token_blacklist app)
    'UPDATE_LAST_LOGIN': False,                     # Set to True if you want to update User.last_login

    'ALGORITHM': 'HS256',                           # Default algorithm for symmetric keys
    'SIGNING_KEY': os.environ.get('SECRET_KEY'), # Crucial: uses your Django SECRET_KEY for signing

    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,

    'AUTH_HEADER_TYPES': ('Bearer',),               # Standard header type
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',                          # Field in your user model for user ID
    'USER_ID_CLAIM': 'user_id',                     # Claim name in the token payload for user ID
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',

    'JTI_CLAIM': 'jti',

    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

#Email Configuration (common parts, sensitive parts in production.py)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 465
EMAIL_USE_TLS = False # This should be True in production, but let's put it there
EMAIL_USE_SSL = True # This too

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Auth Model
AUTH_USER_MODEL = 'users.User'

# Internationalization
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Africa/Lagos' # Changed to Lagos as per context

USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles') # For collectstatic

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'mediafiles') # For user uploads


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

APPEND_SLASH = True

# CORS (will be refined in production.py)
CORS_ALLOWED_ORIGINS = os.environ.get('FRONTEND_URL', '').split(',')

# Redis configuration (common parts)
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', default='amqp://guest:guest@localhost:5672//') # For RabbitMQ
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Lagos' # Consistent with TIME_ZONE
CELERY_ENABLE_UTC = True # Always good practice
CELERY_RESULT_BACKEND = 'django-db'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'verbose': {
            'format': '{asctime} [{levelname}] {name} - {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
    },

    'handlers': {
        'file_info': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/info.log'),
            'formatter': 'verbose',
        },
        'file_error': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/error.log'),
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },

    'loggers': {
        'django': {
            'handlers': ['console', 'file_info', 'file_error'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['file_error'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}