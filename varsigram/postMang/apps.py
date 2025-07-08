from django.apps import AppConfig
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from firebase_admin import storage
import os
from django.conf import settings
# import json # No longer strictly needed if only using file path, but harmless to keep

# Global variables to store initialized clients
_firestore_db_client = None
_firebase_app_instance = None
_firebase_storage_client = None

class FirebaseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'postMang'

    def ready(self):
        """
        Initializes Firebase Admin SDK when the Django app is ready.
        This method is called only once when Django starts up.
        """
        global _firestore_db_client
        global _firebase_app_instance
        global _firebase_storage_client

        # Initialize the Firebase app only once
        if not firebase_admin._apps:
            # --- Determine the path to your service account key file ---
            cred_path = None
            if settings.ENVIRONMENT == 'production':
                # For production, prioritize environment variable for path
                cred_path = os.environ.get('FIREBASE_CREDENTIALS_PATH')
                if not cred_path:
                    # Fallback or strict error if not set for prod
                    print("Error: FIREBASE_CREDENTIALS_PATH environment variable not set for production.")
                    raise RuntimeError("Firebase production credentials path not configured.")
            else: # Development
                # For development, you might have a local file
                cred_path = os.environ.get('FIREBASE_CREDENTIALS_PATH')
                if not cred_path:
                    # Fallback to a common local path if env var isn't set for dev
                    print("FIREBASE_CREDENTIALS_PATH environment variable not set. Falling back to local path.")
                    cred_path = os.path.join(settings.BASE_DIR, 'config', 'dev-firebase-adminsdk.json') # Example dev path

            if not cred_path:
                error_msg = "Firebase credentials path not determined for the current environment."
                print(f"Error: {error_msg}")
                raise RuntimeError(error_msg)

            if not os.path.exists(cred_path):
                error_msg = f"Firebase service account key file not found at: {cred_path}"
                print(f"Error: {error_msg}")
                raise RuntimeError(error_msg)

            try:
                # --- THIS IS THE CORRECT WAY TO USE THE FILE PATH ---
                cred = credentials.Certificate(cred_path)
                print(f"Firebase credentials loaded from file: {cred_path}")
            except Exception as e:
                print(f"Error loading Firebase credentials from file {cred_path}: {e}")
                raise # Critical error during credential creation

            # Single project ID (if you have one project with multiple DBs/Buckets)
            firebase_project_id = os.environ.get('FIREBASE_PROJECT_ID') 
            options = {}
            if firebase_project_id:
                options['projectId'] = firebase_project_id
            
            # Initialize the main Firebase app instance
            _firebase_app_instance = firebase_admin.initialize_app(cred, options)
            print(f"Firebase Admin SDK initialized for project: {options.get('projectId', 'N/A')}.")

        # --- Initialize Firestore Client ---
        firestore_database_id = None
        if settings.ENVIRONMENT == 'production':
            firestore_database_id = os.environ.get('FIRESTORE_DB_ID')
            if not firestore_database_id:
                print("Warning: FIRESTORE_PROD_DB_ID not set. Using (default) Firestore database.")
        else: # Development
            firestore_database_id = os.environ.get('FIRESTORE_DB_ID')
            if not firestore_database_id:
                error_msg = "FIRESTORE_DEV_DB_ID not set for development. Cannot connect to dev Firestore."
                print(f"Error: {error_msg}")
                raise RuntimeError(error_msg)

        try:
            _firestore_db_client = firestore.client(app=_firebase_app_instance, database_id=firestore_database_id)
            print(f"Firestore client connected to database: {firestore_database_id or '(default)'}.")
        except Exception as e:
            print(f"Error connecting to Firestore database {firestore_database_id or '(default)'}: {e}")
            raise

        # --- Initialize Cloud Storage Client ---
        storage_bucket_name = None
        if settings.ENVIRONMENT == 'production':
            storage_bucket_name = os.environ.get('FIREBASE_STORAGE_BUCKET')
            if not storage_bucket_name:
                print("Warning: FIREBASE_PROD_STORAGE_BUCKET not set. Using (default) Storage bucket.")
        else: # Development
            storage_bucket_name = os.environ.get('FIREBASE_STORAGE_BUCKET')
            if not storage_bucket_name:
                error_msg = "FIREBASE_DEV_STORAGE_BUCKET not set for development. Cannot connect to dev Storage."
                print(f"Error: {error_msg}")
                raise RuntimeError(error_msg)
        
        try:
            _firebase_storage_client = storage.bucket(name=storage_bucket_name, app=_firebase_app_instance)
            print(f"Firebase Storage client connected to bucket: {storage_bucket_name}.")
        except Exception as e:
            print(f"Error connecting to Storage bucket {storage_bucket_name}: {e}")
            raise

# Utility functions remain the same
def get_firestore_db():
    if _firestore_db_client is None:
        raise RuntimeError("Firestore client not initialized. Ensure Django app is ready.")
    return _firestore_db_client

def get_firebase_storage_client():
    if _firebase_storage_client is None:
        raise RuntimeError("Firebase Storage client not initialized. Ensure Django app is ready.")
    return _firebase_storage_client