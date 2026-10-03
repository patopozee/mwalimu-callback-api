import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st

def initialize_firebase():
    # Only initialize if the app hasn't been initialized yet
    if not firebase_admin._apps:
        # 1. PRODUCTION RAILWAY FIRST: If running on Railway, look for the environment variable
        raw_creds = os.environ.get("FIREBASE_CREDENTIALS")
        
        if raw_creds is not None:
            try:
                # Sanitize out any rogue carriage returns or trailing spaces
                clean_creds = raw_creds.strip().lstrip('\ufeff')
                if clean_creds.startswith("'") and clean_creds.endswith("'"):
                    clean_creds = clean_creds[1:-1].strip()
                    
                cred_dict = json.loads(clean_creds)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
            except Exception as parse_error:
                raise RuntimeError(f"Failed to parse FIREBASE_CREDENTIALS environment string: {str(parse_error)}")
                
        # 2. LOCAL LOCALHOST TESTING FALLBACK: Only touch st.secrets if environment vars are empty
        else:
            try:
                # This block only executes on localhost where secrets.toml exists
                if "firebase" in st.secrets and "service_account_json" in st.secrets["firebase"]:
                    raw_json_str = st.secrets["firebase"]["service_account_json"]
                    cred_dict = json.loads(raw_json_str)
                    cred = credentials.Certificate(cred_dict)
                    firebase_admin.initialize_app(cred)
                else:
                    firebase_admin.initialize_app()
            except Exception as e:
                # If st.secrets fails locally or finds nothing, try a generic fallback
                if os.path.exists("serviceAccountKey.json"):
                    cred = credentials.Certificate("serviceAccountKey.json")
                    firebase_admin.initialize_app(cred)
                else:
                    firebase_admin.initialize_app()
                
    return firestore.client()

db = initialize_firebase()
