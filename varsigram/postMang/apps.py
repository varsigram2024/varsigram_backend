from django.apps import AppConfig
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import os
from django.conf import settings


db = None

class FirebaseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'postMang'

    def ready(self):
        global db # Declare db as global so you can assign to it
        
        # Check if Firebase is already initialized to prevent errors on reload
        if not firebase_admin._apps:
            # Path to your service account key file
            # Best practice: use os.path.join for path construction
            # and verify the path exists, or load from ENV var directly.
            cred_path = os.environ.get('FIREBASE_CREDENTIALS_PATH')
            if not cred_path:
                # Fallback or error if env var isn't set for production
                print("FIREBASE_CREDENTIALS_PATH environment variable not set. Falling back to local path.")
                cred_path = os.path.join(settings.BASE_DIR, 'config', 'versigram-pd-firebase-adminsdk.json') # Example local path

            if not os.path.exists(cred_path):
                print(f"Error: Firebase service account key not found at {cred_path}")
                # You might want to raise an exception or handle this more robustly
                return # Prevent initialization if key is missing

            cred = credentials.Certificate(cred_path)
            
            firebase_admin.initialize_app(cred)
            print("Firebase Admin SDK initialized.")
        
        # Initialize Firestore client after the main app is initialized
        db = firestore.client()
        print("Firestore client connected successfully.")
        
