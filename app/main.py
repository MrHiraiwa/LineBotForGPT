import os
import json
from datetime import datetime, timedelta
from hashlib import md5
import base64
from Crypto.Cipher import AES
from google.cloud import firestore
import requests
from flask import Flask, request

app = Flask(__name__)

SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
OPENAI_APIKEY = os.getenv('OPENAI_APIKEY')
LINE_ACCESS_TOKEN = os.getenv('LINE_ACCESS_TOKEN')
MAX_DAILY_USAGE = int(os.getenv('MAX_DAILY_USAGE'))
MAX_TOKEN_NUM = 2000
SECRET_KEY = b'secret'

errorMessage = '現在アクセスが集中しているため、しばらくしてからもう一度お試しください。'
countMaxMessage = f'1日の最大使用回数{MAX_DAILY_USAGE}回を超過しました。'

systemPrompt = """
あなたはユーザーの親友です。
ユーザーと気さくに話します。
"""

def systemRole():
    return { "role": "system", "content": systemPrompt }

def hashString(userId, m):
    hash = md5(userId.encode()).hexdigest()
    hash = int(hash, 16)
    return (hash % m) + 1

def get_encrypted_message(message, secret_key):
    cipher = AES.new(secret_key, AES.MODE_ECB)
    message = message + (16 - len(message) % 16) * "\0"
    enc_message = base64.b64encode(cipher.encrypt(message))
    return enc_message.decode()

def get_decrypted_message(enc_message, secret_key):
    cipher = AES.new(secret_key, AES.MODE_ECB)
    message = cipher.decrypt(base64.b64decode(enc_message))
    return message.decode()

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
    event = request.json['events'][0]
    replyToken = event['replyToken']
    userId = event['source']['userId']
    nowDate = datetime.now()

    db = firestore.Client()
    doc_ref = db.collection(u'users').document(userId)
    doc = doc_ref.get()

    if doc.exists:
        user = doc.to_dict()
        dailyUsage = user.get('dailyUsage', 0)
        user['messages'] = [{**msg, 'content': get_decrypted_message(msg['content'], SECRET_KEY)} for msg in user['messages']]

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
    elif MAX_DAILY_USAGE and MAX_DAILY_USAGE <= dailyUsage:
        callLineApi(countMaxMessage, replyToken)
        return 'OK', 200

    messages = user['messages'] + [{'role': 'user', 'content': userMessage}]
    messages = [systemRole()] + messages[-(MAX_TOKEN_NUM-1):]  # keep messages within MAX_TOKEN_NUM

    response = requests.post(
        'https://api.openai.com/v1/chat/completions',
        headers={'Authorization': f'Bearer {OPENAI_APIKEY}'},
        json={'model': 'gpt-3.5-turbo', 'messages': messages}
    )
    botReply = response.json()['choices'][0]['message']['content'].trim()

    user['messages'].append({'role': 'assistant', 'content': get_encrypted_message(botReply, SECRET_KEY)})
    user['updatedDateString'] = nowDate
    user['dailyUsage'] += 1
    doc_ref.set(user)

    callLineApi(botReply, replyToken)
    return 'OK', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
