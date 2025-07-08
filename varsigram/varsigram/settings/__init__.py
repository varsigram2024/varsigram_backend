import os

# Define environment variables to control settings loading
# Default to 'development' if DJANGO_SETTINGS_MODULE_ENV is not set
ENVIRONMENT = os.getenv('DJANGO_SETTINGS_MODULE_ENV', 'development')

if ENVIRONMENT == 'production':
    from .production import *
elif ENVIRONMENT == 'development':
    from .development import *
else:
    # Handle other environments or raise an error for unknown ones
    raise ImportError(f"Unknown DJANGO_SETTINGS_MODULE_ENV '{ENVIRONMENT}'. Must be 'development' or 'production'.")