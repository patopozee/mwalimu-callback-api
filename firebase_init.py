import firebase_admin
from firebase_admin import credentials, firestore

def initialize_firebase():
    # Only initialize if the app hasn't been initialized yet
    if not firebase_admin._apps:
        # Use Application Default Credentials (ADC) provided by Cloud Run automatically
        firebase_admin.initialize_app()
    return firestore.client()

db = initialize_firebase()
