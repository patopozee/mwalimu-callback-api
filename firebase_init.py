import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

def initialize_firebase():
    # Only initialize if the app hasn't been initialized yet
    if not firebase_admin._apps:
        # 1. Read the raw string from the Railway environment variables
        raw_creds = os.environ.get("FIREBASE_CREDENTIALS")
        
        if raw_creds:
            try:
                # --- SANITIZATION BLOCK ---
                # Strip out any hidden whitespace or Windows BOM characters
                clean_creds = raw_creds.strip().lstrip('\ufeff')
                
                # If the string got accidentally wrapped in literal single quotes, strip them
                if clean_creds.startswith("'") and clean_creds.endswith("'"):
                    clean_creds = clean_creds[1:-1].strip()
                # --------------------------

                # Parse the sanitized string safely
                cred_dict = json.loads(clean_creds)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
            except Exception as parse_error:
                raise RuntimeError(f"Failed to parse FIREBASE_CREDENTIALS string: {str(parse_error)}")
        else:
            # 2. Fallback behaviors for alternative setups
            if os.path.exists("serviceAccountKey.json"):
                cred = credentials.Certificate("serviceAccountKey.json")
                firebase_admin.initialize_app(cred)
            else:
                firebase_admin.initialize_app()
                
    return firestore.client()

db = initialize_firebase()
