from google.cloud import firestore

REQUIRED_ENV_VARS = [
    "OPENAI_APIKEY",
    "LINE_ACCESS_TOKEN",
    "MAX_DAILY_USAGE",
    "SECRET_KEY",
    "SYSTEM_PROMPT",
    "MAX_TOKEN_NUM"
]

def get_setting(key):
    db = firestore.Client()
    doc_ref = db.collection(u'settings').document(key)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict().get('value')
    else:
        return None

def update_setting(key, value):
    db = firestore.Client()
    doc_ref = db.collection(u'settings').document(key)
    doc_ref.set({'value': value})

def check_env_vars():
    missing_vars = [var for var in REQUIRED_ENV_VARS if get_setting(var) is None]
    if missing_vars:
        missing_vars_str = ", ".join(missing_vars)
        print(f"Missing required settings in Firestore: {missing_vars_str}")
        return False
    return True
