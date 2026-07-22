import json
import firebase_admin
import streamlit as st

from firebase_admin import credentials, firestore


def initialize_firebase():

    if not firebase_admin._apps:

        raw_json = st.secrets["firebase"]["service_account_json"]

        cred_dict = json.loads(raw_json)

        cred = credentials.Certificate(cred_dict)

        firebase_admin.initialize_app(cred)

    return firestore.client()


db = initialize_firebase()