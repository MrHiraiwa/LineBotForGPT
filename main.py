import os
import json
from datetime import datetime, timedelta
from hashlib import md5
import base64
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
import requests
from pytz import utc, timezone
from flask import Flask, request, render_template, session, redirect, url_for, abort
from google.cloud import firestore

jst = timezone('Asia/Tokyo')
nowDate = datetime.utcnow().replace(tzinfo=utc)
nowDate = nowDate.astimezone(jst)


try:
    db = firestore.Client()
except Exception as e:
    print(f"Error creating Firestore client: {e}")
    raise

    
def get_setting(key):
    doc_ref = db.collection(u'settings').document('app_settings')  # Changed to 'app_settings'
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict().get(key)  # Get the value of the key
    else:
        # Create default setting if it doesn't exist
        if key in ['MAX_TOKEN_NUM', 'MAX_DAILY_USAGE']:
            default_value = 2000  # Default value for integer settings
        else:
            default_value = ""  # Replace with your actual default value
        doc_ref.set({key: default_value})  # Set the key with the default value
        return default_value

def update_setting(key, value):
    doc_ref = db.collection(u'settings').document('app_settings')
    doc_ref.update({key: value})

MAX_TOKEN_NUM = int(get_setting('MAX_TOKEN_NUM') or 2000)
OPENAI_APIKEY = get_setting('OPENAI_APIKEY')
LINE_ACCESS_TOKEN = get_setting('LINE_ACCESS_TOKEN')
MAX_DAILY_USAGE = int(get_setting('MAX_DAILY_USAGE') or 0)
SECRET_KEY = get_setting('SECRET_KEY')
SYSTEM_PROMPT = get_setting('SYSTEM_PROMPT')
ERROR_MESSAGE = get_setting('ERROR_MESSAGE')
BOT_NAME = get_setting('BOT_NAME')

app = Flask(__name__)
hash_object = SHA256.new(data=(SECRET_KEY or '').encode('utf-8'))
hashed_secret_key = hash_object.digest()
app.secret_key = SECRET_KEY

import hashlib

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

@app.route('/set_admin_password', methods=['GET', 'POST'])
def set_admin_password():
    existing_password = get_setting('ADMIN_PASSWORD')
    if existing_password is not None:
        abort(403)  # Abort if a password is already set
    if request.method == 'POST':
        password = request.form.get('password')
        hashed_password = hash_password(password)
        update_setting('ADMIN_PASSWORD', hashed_password)

        secret_key = request.form.get('secret_key')
        update_setting('SECRET_KEY', secret_key)

        # Update the Flask app's secret key
        app.secret_key = secret_key
        
        return redirect(url_for('login'))
    else:
        return '''
            <form method="post">
                Set Password: <input type="password" name="password"><br>
                Set Secret Key: <input type="text" name="secret_key"><br>
                <input type="submit" value="Set Password and Secret Key">
            </form>
        '''



@app.route('/login', methods=['GET', 'POST'])
def login():
    admin_password = get_setting('ADMIN_PASSWORD')
    if admin_password is None:
        return redirect(url_for('set_admin_password'))
    if request.method == 'POST':
        password = request.form.get('password')
        hashed_password = hash_password(password)
        if hashed_password == admin_password:
            session['is_admin'] = True
            return redirect(url_for('settings'))
        else:
            return "Invalid password", 401
    else:
        return '''
            <form method="post">
                Password: <input type="password" name="password">
                <input type="submit" value="Login">
            </form>
        '''

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if 'is_admin' not in session or not session['is_admin']:
        return redirect(url_for('login'))
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        hashed_current_password = hash_password(current_password)
        admin_password = get_setting('ADMIN_PASSWORD')
        if hashed_current_password == admin_password:
            hashed_new_password = hash_password(new_password)
            update_setting('ADMIN_PASSWORD', hashed_new_password)
            return redirect(url_for('settings'))
        else:
            return "Invalid current password", 401
    else:
        return '''
            <form method="post">
                Current Password: <input type="password" name="current_password"><br>
                New Password: <input type="password" name="new_password"><br>
                <input type="submit" value="Reset Password">
            </form>
        '''

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'is_admin' not in session or not session['is_admin']:
        return redirect(url_for('login'))
    if request.method == 'POST':
        # Update settings
        for key in REQUIRED_ENV_VARS:
            value = request.form.get(key)
            if value:
                update_setting(key, value)

    # Fetch current settings
    current_settings = {key: get_setting(key) for key in REQUIRED_ENV_VARS}
    return render_template('settings.html', settings=current_settings, reset_password_url=url_for('reset_password'))

countMaxMessage = f'1日の最大使用回数{MAX_DAILY_USAGE}回を超過しました。'

REQUIRED_ENV_VARS = [
    "OPENAI_APIKEY",
    "LINE_ACCESS_TOKEN",
    "MAX_DAILY_USAGE",
    "BOT_NAME",
    "SYSTEM_PROMPT",
    "MAX_TOKEN_NUM",
    "ERROR_MESSAGE"
]

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

    # Fetch current settings
    current_settings = {key: get_setting(key) for key in REQUIRED_ENV_VARS}
    return render_template('settings.html', settings=current_settings)

@app.route('/', methods=['POST'])
def lineBot():
    try:
        if 'events' not in request.json or not request.json['events']:
            return 'No events in the request', 200  # Return a 200 HTTP status code

        # 以下のコードが修正されました
        event = request.json['events'][0]
        replyToken = event['replyToken']
        userId = event['source']['userId']
        nowDate = datetime.utcnow().replace(tzinfo=utc)  # Explicitly set timezone to UTC
        line_profile = json.loads(get_profile(userId).text)
        display_name = line_profile['displayName']
        act_as = BOT_NAME + "として返信して。\n"
        nowDateStr = nowDate.strftime('%Y-%m-%d %H:%M:%S')

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

            user['messages'].append({'role': 'user', 'content': nowDateStr + " " + act_as + display_name + ":" + userMessage})
        
            # Remove old logs if the total characters exceed 2000 before sending to the API.
            total_chars = len(SYSTEM_PROMPT) + sum([len(msg['content']) for msg in user['messages']])
            while total_chars > MAX_TOKEN_NUM and len(user['messages']) > 0:
                removed_message = user['messages'].pop(0)  # Remove the oldest message
                total_chars -= len(removed_message['content'])

            messages = user['messages']

            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={'Authorization': f'Bearer {OPENAI_APIKEY}'},
                json={'model': 'gpt-3.5-turbo', 'messages': [systemRole()] + messages},
                timeout=10  # 10 seconds timeout for example
            )

            response_json = response.json()

            # Error handling
            if response.status_code != 200 or 'error' in response_json:
                print(f"OpenAI error: {response_json.get('error', 'No response from API')}")
                callLineApi(ERROR_MESSAGE, replyToken)
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
    except KeyError:
        return 'Not a valid JSON', 200  # Return a 200 HTTP status code
    except Exception as e:
        print(f"Error in lineBot: {e}")
        callLineApi(ERROR_MESSAGE, replyToken)
        raise

def get_profile(userId):
    url = 'https://api.line.me/v2/bot/profile/' + userId
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Authorization": "Bearer " + LINE_ACCESS_TOKEN,
    }
    response = requests.get(url, headers=headers, timeout=5)  # Timeout after 5 seconds
    return response

