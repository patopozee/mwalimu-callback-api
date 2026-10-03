import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st

def initialize_firebase():
    # Only initialize if the app hasn't been initialized yet
    if not firebase_admin._apps:
        # 1. LOCAL LOCALHOST TESTING: Read directly from your .streamlit/secrets.toml file
        if "firebase" in st.secrets and "service_account_json" in st.secrets["firebase"]:
            try:
                # Pull the string straight from your secrets configuration
                raw_json_str = st.secrets["firebase"]["service_account_json"]
                cred_dict = json.loads(raw_json_str)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
            except Exception as e:
                raise RuntimeError(f"Failed to parse Firebase JSON from secrets.toml: {str(e)}")
                
        # 2. PRODUCTION RAILWAY FALLBACK: Read from the cloud environment variable
        else:
            raw_creds = os.environ.get("FIREBASE_CREDENTIALS")
            if raw_creds is not None:  # <-- THE CRITICAL FIX FOR PYLANCE
                try:
                    clean_creds = raw_creds.strip().lstrip('\ufeff')
                    if clean_creds.startswith("'") and clean_creds.endswith("'"):
                        clean_creds = clean_creds[1:-1].strip()
                    cred_dict = json.loads(clean_creds)
                    cred = credentials.Certificate(cred_dict)
                    firebase_admin.initialize_app(cred)
                except Exception as parse_error:
                    raise RuntimeError(f"Failed to parse FIREBASE_CREDENTIALS environment string: {str(parse_error)}")
            else:
                # 3. Default Fallback
                firebase_admin.initialize_app()
                
    return firestore.client()

db = initialize_firebase()
