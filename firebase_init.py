import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

def initialize_firebase():
    # Only initialize if the app hasn't been initialized yet
    if not firebase_admin._apps:
        # 1. Read the shared production key from the Railway environment variable
        firebase_creds_json = os.environ.get("FIREBASE_CREDENTIALS")
        
        if firebase_creds_json:
            try:
                # Parse the JSON config string cleanly out of environment memory
                cred_dict = json.loads(firebase_creds_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
            except Exception as parse_error:
                # Absolute emergency fallback layout string logic to capture JSON issues
                raise RuntimeError(f"Failed to parse FIREBASE_CREDENTIALS string: {str(parse_error)}")
        else:
            # 2. Fallback to empty initialization if running locally on GCP toolchains 
            # Or look for a local development fallback file asset
            if os.path.exists("serviceAccountKey.json"):
                cred = credentials.Certificate("serviceAccountKey.json")
                firebase_admin.initialize_app(cred)
            else:
                # Default back to standard ADC behavior if no manual string or file keys exist
                firebase_admin.initialize_app()
                
    return firestore.client()

db = initialize_firebase()
