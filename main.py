import os
import json
from datetime import datetime, timedelta
from hashlib import md5
import base64
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from google.cloud import firestore
import requests
from flask import Flask, request
from pytz import utc

app = Flask(__name__)

OPENAI_APIKEY = os.getenv('OPENAI_APIKEY')
LINE_ACCESS_TOKEN = os.getenv('LINE_ACCESS_TOKEN')
MAX_DAILY_USAGE = int(os.getenv('MAX_DAILY_USAGE'))
MAX_TOKEN_NUM = 2000
SECRET_KEY = os.getenv('SECRET_KEY')
hash_object = SHA256.new(data=SECRET_KEY.encode('utf-8'))
hashed_secret_key = hash_object.digest()

errorMessage = '現在アクセスが集中しているため、しばらくしてからもう一度お試しください。'
countMaxMessage = f'1日の最大使用回数{MAX_DAILY_USAGE}回を超過しました。'

SYSTEM_PROMPT = os.getenv('SYSTEM_PROMPT')

REQUIRED_ENV_VARS = [
    "OPENAI_APIKEY",
    "LINE_ACCESS_TOKEN",
    "MAX_DAILY_USAGE",
    "SECRET_KEY",
    "SYSTEM_PROMPT"
]

def check_env_vars():
    missing_vars = [var for var in REQUIRED_ENV_VARS if os.getenv(var) is None]
    if missing_vars:
        missing_vars_str = ", ".join(missing_vars)
        callLineApi(f"Missing required environment variables: {missing_vars_str}", replyToken)  # Replace replyToken with actual token
        return False
    return True

def systemRole():
    return { "role": "system", "content": SYSTEM_PROMPT }

def get_encrypted_message(message, hashed_secret_key):
    cipher = AES.new(hashed_secret_key, AES.MODE_ECB)
    message = message.encode('utf-8')
    padding = 16 - len(message) % 16
    message += bytes([padding]) * padding
    enc_message = base64.b64encode(cipher.encrypt(message))
    return enc_message.decode()

def get_decrypted_message(enc_message, hashed_secret_key):
    try:
        cipher = AES.new(hashed_secret_key, AES.MODE_ECB)
        enc_message = base64.b64decode(enc_message.encode('utf-8'))
        message = cipher.decrypt(enc_message)
        padding = message[-1]
        if padding > 16:
            raise ValueError("Invalid padding value")
        message = message[:-padding]
        return message.decode().rstrip("\0")
    except Exception as e:
        print(f"Error decrypting message: {e}")
        return None
    
def isBeforeYesterday(date, now):
    today = now.date()
    return today > date

def callLineApi(replyText, replyToken):
    url = 'https://api.line.me/v2/bot/message/reply'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_ACCESS_TOKEN}'
    }
    data = {
        'replyToken': replyToken,
        'messages': [{'type': 'text', 'text': replyText}]
    }
    requests.post(url, headers=headers, data=json.dumps(data))

@app.route('/', methods=['POST'])
def lineBot():
    if not request.json or 'events' not in request.json or len(request.json['events']) == 0:
        return 'OK', 200
    if not check_env_vars():
        return 'OK', 200
    
    event = request.json['events'][0]
    replyToken = event['replyToken']
    userId = event['source']['userId']
    nowDate = datetime.utcnow().replace(tzinfo=utc)  # Explicitly set timezone to UTC

    db = firestore.Client()
    doc_ref = db.collection(u'users').document(userId)

    # Start a Firestore transaction
    @firestore.transactional
    def update_in_transaction(transaction, doc_ref):
        doc = doc_ref.get(transaction=transaction)
        
        dailyUsage = 0
        userMessage = event['message'].get('text')
        
        if doc.exists:
            user = doc.to_dict()
            dailyUsage = user.get('dailyUsage', 0)
            user['messages'] = [{**msg, 'content': get_decrypted_message(msg['content'], hashed_secret_key)} for msg in user['messages']]
            if (nowDate - user['updatedDateString']) > timedelta(days=1):
                dailyUsage = 0
        else:
            user = {
                'userId': userId,
                'messages': [],
                'updatedDateString': nowDate,
                'dailyUsage': 0
            }

        if not userMessage:
            return 'OK'
        elif userMessage.strip() in ["忘れて", "わすれて"]:
            user['messages'] = []
            user['updatedDateString'] = nowDate
            callLineApi('記憶を消去しました。', replyToken)
        elif MAX_DAILY_USAGE is not None and dailyUsage is not None and MAX_DAILY_USAGE <= dailyUsage:
            callLineApi(countMaxMessage, replyToken)
            return 'OK'

        user['messages'].append({'role': 'user', 'content': userMessage})
        
        # Remove old logs if the total characters exceed 2000 before sending to the API.
        total_chars = len(SYSTEM_PROMPT) + sum([len(msg['content']) for msg in user['messages']])
        while total_chars > MAX_TOKEN_NUM and len(user['messages']) > 0:
            removed_message = user['messages'].pop(0)  # Remove the oldest message
            total_chars -= len(removed_message['content'])

        messages = user['messages']

        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={'Authorization': f'Bearer {OPENAI_APIKEY}'},
            json={'model': 'gpt-3.5-turbo', 'messages': [systemRole()] + messages}
        )
        
        response_json = response.json()

        # Error handling
        if 'error' in response_json:
            print(f"OpenAI error: {response_json['error']}")
            return 'OK'  # Return OK to prevent LINE bot from retrying

        botReply = response_json['choices'][0]['message']['content'].strip()

        user['messages'].append({'role': 'assistant', 'content': botReply})
        user['updatedDateString'] = nowDate
        user['dailyUsage'] += 1

        transaction.set(doc_ref, {**user, 'messages': [{**msg, 'content': get_encrypted_message(msg['content'], hashed_secret_key)} for msg in user['messages']]})

        callLineApi(botReply, replyToken)
        return 'OK'

    # Begin the transaction
    return update_in_transaction(db.transaction(), doc_ref)
    
