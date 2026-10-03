import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

def initialize_firebase():
    if not firebase_admin._apps:
        # 1. PRODUCTION CHECK FIRST: Look for the environment variable on Railway
        raw_creds = os.environ.get("FIREBASE_CREDENTIALS")
        
        if raw_creds is not None:
            try:
                clean_creds = raw_creds.strip().lstrip('\ufeff')
                if clean_creds.startswith("'") and clean_creds.endswith("'"):
                    clean_creds = clean_creds[1:-1].strip()
                    
                cred_dict = json.loads(clean_creds)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
            except Exception as parse_error:
                raise RuntimeError(f"Failed to parse FIREBASE_CREDENTIALS environment string: {str(parse_error)}")
                
        # 2. LOCAL LOCALHOST TESTING FALLBACK: Check if running via streamlit locally
        else:
            try:
                import streamlit as st
                if "firebase" in st.secrets and "service_account_json" in st.secrets["firebase"]:
                    raw_json_str = st.secrets["firebase"]["service_account_json"]
                    cred_dict = json.loads(raw_json_str)
                    cred = credentials.Certificate(cred_dict)
                    firebase_admin.initialize_app(cred)
                else:
                    firebase_admin.initialize_app()
            except Exception:
                # If st.secrets throws an error because secrets.toml is missing, try a file fallback
                if os.path.exists("serviceAccountKey.json"):
                    cred = credentials.Certificate("serviceAccountKey.json")
                    firebase_admin.initialize_app(cred)
                else:
                    firebase_admin.initialize_app()
                
    return firestore.client()

db = initialize_firebase()
