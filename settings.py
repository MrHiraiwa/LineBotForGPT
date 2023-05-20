from google.cloud import firestore

def get_setting(key):
    db = firestore.Client()
    doc_ref = db.collection(u'settings').document(key)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict().get('value')
    else:
        return None

MAX_TOKEN_NUM = int(get_setting('MAX_TOKEN_NUM') or 2000)
OPENAI_APIKEY = get_setting('OPENAI_APIKEY')
LINE_ACCESS_TOKEN = get_setting('LINE_ACCESS_TOKEN')
MAX_DAILY_USAGE = int(get_setting('MAX_DAILY_USAGE') or 0)
SECRET_KEY = get_setting('SECRET_KEY')
SYSTEM_PROMPT = get_setting('SYSTEM_PROMPT')

REQUIRED_ENV_VARS = [
    "OPENAI_APIKEY",
    "LINE_ACCESS_TOKEN",
    "MAX_DAILY_USAGE",
    "SECRET_KEY",
    "SYSTEM_PROMPT",
    "MAX_TOKEN_NUM"
]
