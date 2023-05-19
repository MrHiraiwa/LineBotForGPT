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
    cipher = AES.new(hashed_secret_key, AES.MODE_ECB)
    enc_message = base64.b64decode(enc_message.encode('utf-8'))
    message = cipher.decrypt(enc_message)
    padding = message[-1]
    message = message[:-padding]
    return message.decode().rstrip("\0")


def isBeforeYesterday(date, now):
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
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
    
    event = request.json['events'][0]
    replyToken = event['replyToken']
    userId = event['source']['userId']
    nowDate = datetime.now()

    db = firestore.Client()
    doc_ref = db.collection(u'users').document(userId)
    doc = doc_ref.get()

    dailyUsage = 0

    if doc.exists:
        user = doc.to_dict()
        dailyUsage = user.get('dailyUsage', 0)
        user['messages'] = [{**msg, 'content': get_decrypted_message(msg['content'], hashed_secret_key)} for msg in user['messages']]

        if isBeforeYesterday(user['updatedDateString'].date(), nowDate):
            dailyUsage = 0
    else:
        user = {
            'userId': userId,
            'messages': [],
            'updatedDateString': nowDate,
            'dailyUsage': 0
        }

    userMessage = event['message'].get('text')
    if not userMessage:
        return 'OK', 200
    elif userMessage.strip() in ["忘れて", "わすれて"]:
        user['messages'] = []
        doc_ref.set(user)
        callLineApi('記憶を消去しました。', replyToken)
        return 'OK', 200
    elif MAX_DAILY_USAGE is not None and dailyUsage is not None and MAX_DAILY_USAGE <= dailyUsage:
        callLineApi(countMaxMessage, replyToken)
        return 'OK', 200

    # Save user message first
    encryptedUserMessage = get_encrypted_message(userMessage, hashed_secret_key)
    user['messages'].append({'role': 'user', 'content': encryptedUserMessage})

    # Remove old logs if the total characters exceed 2000 before sending to the API.
    total_chars = len(SYSTEM_PROMPT) + sum([len(msg['content']) for msg in user['messages']])
    while total_chars > MAX_TOKEN_NUM and len(user['messages']) > 0:
        removed_message = user['messages'].pop(0)  # Remove the oldest message
        total_chars -= len(removed_message['content'])

    doc_ref.set(user)

    # Use the non-encrypted messages for the API
    messages = user['messages'] + [{'role': 'user', 'content': userMessage}]

    response = requests.post(
        'https://api.openai.com/v1/chat/completions',
        headers={'Authorization': f'Bearer {OPENAI_APIKEY}'},
        json={'model': 'gpt-3.5-turbo', 'messages': [systemRole()] + messages}
    )
    botReply = response.json()['choices'][0]['message']['content'].strip()

    # Save bot response after received
    user['messages'].append({'role': 'assistant', 'content': get_encrypted_message(botReply, hashed_secret_key)})
    user['updatedDateString'] = nowDate
    user['dailyUsage'] += 1

    doc_ref.set(user)

    callLineApi(botReply, replyToken)
    return 'OK', 200
