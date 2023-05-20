import os
from hashlib import sha256
from flask import Flask
from google.cloud import firestore

from settings import get_setting, SECRET_KEY

app = Flask(__name__)
hash_object = sha256(data=(SECRET_KEY or '').encode('utf-8'))
hashed_secret_key = hash_object.digest()
app.secret_key = SECRET_KEY
