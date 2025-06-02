import firebase_admin
from firebase_admin import credentials, auth, firestore

# Download the service account key from Firebase Console
cred = credentials.Certificate('./config/versigram-pd-firebase-adminsdk.json')

# Initialize Firebase
firebase_admin.initialize_app(cred)

# Initialize Firestore (if needed)
db = firestore.client()