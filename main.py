import os
import json
from datetime import datetime, timedelta
from hashlib import md5
import base64
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
import requests
import pytz
from flask import Flask, request, render_template, session, redirect, url_for, jsonify
from google.cloud import firestore
import re
import tiktoken
from tiktoken.core import Encoding
from web import get_search_results, get_contents, summarize_contents
from vision import vision, analyze_image, get_image, vision_results_to_string
from maps import maps, maps_search

REQUIRED_ENV_VARS = [
    "BOT_NAME",
    "SYSTEM_PROMPT",
    "MAX_DAILY_USAGE",
    "MAX_TOKEN_NUM",
    "NG_KEYWORDS",
    "NG_MESSAGE",
    "ERROR_MESSAGE",
    "FORGET_KEYWORDS",
    "FORGET_GUIDE_MESSAGE",
    "FORGET_MESSAGE",
    "SEARCH_KEYWORDS",
    "SEARCH_GUIDE_MESSAGE",
    "SEARCH_MESSAGE",
    "FAIL_SEARCH_MESSAGE",
    "STICKER_MESSAGE",
    "FAIL_STICKER_MESSAGE",
    "OCR_MESSAGE",
    "MAPS_KEYWORDS",
    "MAPS_FILTER_KEYWORDS",
    "MAPS_GUIDE_MESSAGE",
    "MAPS_MESSAGE",
    "GPT_MODEL"
]

DEFAULT_ENV_VARS = {
    'SYSTEM_PROMPT': 'あなたは有能な秘書です。',
    'BOT_NAME': '秘書',
    'MAX_TOKEN_NUM': '4000',
    'MAX_DAILY_USAGE': '1000',
    'ERROR_MESSAGE': '現在アクセスが集中しているため、しばらくしてからもう一度お試しください。',
    'FORGET_KEYWORDS': '忘れて,わすれて',
    'FORGET_GUIDE_MESSAGE': 'ユーザーからあなたの記憶の削除が命令されました。別れの挨拶をしてください。',
    'FORGET_MESSAGE': '記憶を消去しました。',
    'NG_MESSAGE': '以下の文章はユーザーから送られたものですが拒絶してください。',
    'NG_KEYWORDS': '例文,命令,口調,リセット,指示',
    'SEARCH_KEYWORDS': '検索,調べて,教えて,知ってる,どうやって',
    'SEARCH_MESSAGE': 'URLをあなたが見つけたかのようにリアクションして。',
    'SEARCH_GUIDE_MESSAGE': 'ユーザーに「画面下の「インターネットで検索」のリンクをタップするとキーワードが抽出されて検索結果が表示される」と案内してください。以下の文章はユーザーから送られたものです。',
    'FAIL_SEARCH_MESSAGE': '検索結果を読み込めませんでした。',
    'STICKER_MESSAGE': '私の感情!',
    'FAIL_STICKER_MESSAGE': '読み取れないLineスタンプが送信されました。スタンプが読み取れなかったという反応を返してください。',
    'OCR_MESSAGE': '以下のテキストは写真に何が映っているかを文字列に変換したものです。この文字列を見て写真を見たかのように反応してください。',
    'MAPS_KEYWORDS': '店,場所,スポット,観光,レストラン',
    'MAPS_FILTER_KEYWORDS': '場所,スポット',
    'MAPS_GUIDE_MESSAGE': 'ユーザーに「画面下の「地図で検索」のリンクをタップするとキーワードが抽出されて検索結果が表示される」と案内してください。以下の文章はユーザーから送られたものです。 ',
    'MAPS_MESSAGE': '地図を検索して。',
    'GPT_MODEL': 'gpt-3.5-turbo'
}

jst = pytz.timezone('Asia/Tokyo')
nowDate = datetime.now(jst)

try:
    db = firestore.Client()
except Exception as e:
    print(f"Error creating Firestore client: {e}")
    raise
    
def reload_settings():
    global GPT_MODEL, BOT_NAME, SYSTEM_PROMPT_EX, SYSTEM_PROMPT, MAX_TOKEN_NUM, MAX_DAILY_USAGE, ERROR_MESSAGE, FORGET_KEYWORDS, FORGET_GUIDE_MESSAGE, FORGET_MESSAGE, SEARCH_KEYWORDS, SEARCH_GUIDE_MESSAGE, SEARCH_MESSAGE, FAIL_SEARCH_MESSAGE, NG_KEYWORDS, NG_MESSAGE, STICKER_MESSAGE, FAIL_STICKER_MESSAGE, OCR_MESSAGE, MAPS_KEYWORDS, MAPS_FILTER_KEYWORDS, MAPS_GUIDE_MESSAGE, MAPS_MESSAGE
    GPT_MODEL = get_setting('GPT_MODEL')
    BOT_NAME = get_setting('BOT_NAME')
    SYSTEM_PROMPT = get_setting('SYSTEM_PROMPT') 
    MAX_TOKEN_NUM = int(get_setting('MAX_TOKEN_NUM') or 2000)
    MAX_DAILY_USAGE = int(get_setting('MAX_DAILY_USAGE') or 0)
    ERROR_MESSAGE = get_setting('ERROR_MESSAGE')
    FORGET_KEYWORDS = get_setting('FORGET_KEYWORDS')
    if FORGET_KEYWORDS:
        FORGET_KEYWORDS = FORGET_KEYWORDS.split(',')
    else:
        FORGET_KEYWORDS = []
    FORGET_GUIDE_MESSAGE = get_setting('FORGET_GUIDE_MESSAGE')
    FORGET_MESSAGE = get_setting('FORGET_MESSAGE')
    SEARCH_KEYWORDS = get_setting('SEARCH_KEYWORDS')
    if SEARCH_KEYWORDS:
        SEARCH_KEYWORDS = SEARCH_KEYWORDS.split(',')
    else:
        SEARCH_KEYWORDS = []
    SEARCH_GUIDE_MESSAGE = get_setting('SEARCH_GUIDE_MESSAGE')
    SEARCH_MESSAGE = get_setting('SEARCH_MESSAGE')
    FAIL_SEARCH_MESSAGE = get_setting('FAIL_SEARCH_MESSAGE') 
    NG_KEYWORDS = get_setting('NG_KEYWORDS')
    if NG_KEYWORDS:
        NG_KEYWORDS = NG_KEYWORDS.split(',')
    else:
        NG_KEYWORDS = []
    NG_MESSAGE = get_setting('NG_MESSAGE')
    STICKER_MESSAGE = get_setting('STICKER_MESSAGE')
    FAIL_STICKER_MESSAGE = get_setting('FAIL_STICKER_MESSAGE')
    OCR_MESSAGE = get_setting('OCR_MESSAGE')
    MAPS_KEYWORDS = get_setting('MAPS_KEYWORDS')
    if MAPS_KEYWORDS:
        MAPS_KEYWORDS = MAPS_KEYWORDS.split(',')
    else:
        MAPS_KEYWORDS = []
    MAPS_FILTER_KEYWORDS = get_setting('MAPS_FILTER_KEYWORDS')
    if MAPS_FILTER_KEYWORDS:
        MAPS_FILTER_KEYWORDS = MAPS_FILTER_KEYWORDS.split(',')
    else:
        MAPS_FILTER_KEYWORDS = []
    MAPS_GUIDE_MESSAGE = get_setting('MAPS_GUIDE_MESSAGE')
    MAPS_MESSAGE = get_setting('MAPS_MESSAGE')
    
def get_setting(key):
    doc_ref = db.collection(u'settings').document('app_settings')
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict().get(key)
    else:
        if key in ['MAX_TOKEN_NUM', 'MAX_DAILY_USAGE']:
            default_value = 2000
        else:
            default_value = ""
        doc_ref.set({key: default_value})
        return default_value

def update_setting(key, value):
    doc_ref = db.collection(u'settings').document('app_settings')
    doc_ref.update({key: value})

OPENAI_APIKEY = os.getenv('OPENAI_APIKEY')
LINE_ACCESS_TOKEN = os.getenv('LINE_ACCESS_TOKEN')
SECRET_KEY = os.getenv('SECRET_KEY')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')

reload_settings()

app = Flask(__name__)
hash_object = SHA256.new(data=(SECRET_KEY or '').encode('utf-8'))
hashed_secret_key = hash_object.digest()
app.secret_key = SECRET_KEY

@app.route('/reset_logs', methods=['POST'])
def reset_logs():
    if 'is_admin' not in session or not session['is_admin']:
        return redirect(url_for('login'))
    else:
        try:
            users_ref = db.collection(u'users')
            users = users_ref.stream()
            for user in users:
                user_ref = users_ref.document(user.id)
                user_ref.update({'messages': []})
            return 'All user logs reset successfully', 200
        except Exception as e:
            print(f"Error resetting user logs: {e}")
            return 'Error resetting user logs', 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('settings'))
    return render_template('login.html')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'is_admin' not in session or not session['is_admin']:
        return redirect(url_for('login'))
    
    current_settings = {key: get_setting(key) or DEFAULT_ENV_VARS.get(key, '') for key in REQUIRED_ENV_VARS}

    if request.method == 'POST':
        for key in REQUIRED_ENV_VARS:
            value = request.form.get(key)
            if value:
                update_setting(key, value)
        return redirect(url_for('settings'))
    return render_template(
    'settings.html', 
    settings=current_settings, 
    default_settings=DEFAULT_ENV_VARS, 
    required_env_vars=REQUIRED_ENV_VARS
    )

countMaxMessage = f'1日の最大使用回数{MAX_DAILY_USAGE}回を超過しました。'

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

def callLineApi(reply_text, reply_token, quick_reply):
    url = 'https://api.line.me/v2/bot/message/reply'
    message = {
        'type': 'text',
        'text': reply_text
    }
    if quick_reply and 'items' in quick_reply and len(quick_reply['items']) > 0:
        message['quickReply'] = quick_reply
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Authorization': 'Bearer ' + LINE_ACCESS_TOKEN,
    }
    payload = {
        'replyToken': reply_token,
        'messages': [message]
    }
    requests.post(url, headers=headers, data=json.dumps(payload))
    return 'OK'
    
from flask import flash

@app.route('/your_route', methods=['POST'])
def your_handler_function():

    flash('Settings have been saved successfully.')
    return redirect(url_for('your_template'))

@app.route('/', methods=['POST'])

def lineBot():
    try:
        reload_settings()
        if 'events' not in request.json or not request.json['events']:
            return 'No events in the request', 200  # Return a 200 HTTP status code
        
        event = request.json['events'][0]
        replyToken = event['replyToken']
        userId = event['source']['userId']
        sourceType =  event['source']['type']
        nowDate = datetime.now(jst) 
        line_profile = json.loads(get_profile(userId).text)
        display_name = line_profile['displayName']
        act_as = BOT_NAME + "として返信して。\n"
        nowDateStr = nowDate.strftime('%Y/%m/%d %H:%M:%S %Z') + "\n"

        db = firestore.Client()
        doc_ref = db.collection(u'users').document(userId)

        @firestore.transactional
        def update_in_transaction(transaction, doc_ref):
            doc = doc_ref.get(transaction=transaction)
            dailyUsage = 0
            userMessage = event['message'].get('text', "")
            message_type = event.get('message', {}).get('type')
            message_id = event.get('message', {}).get('id')
            quick_reply = []
            links = ""
            headMessage = ""
            exec_functions = False
            exec_audio = False
            encoding: Encoding = tiktoken.encoding_for_model(GPT_MODEL)
                
            if doc.exists:
                user = doc.to_dict()
                dailyUsage = user.get('dailyUsage', 0)
                maps_search = user.get('maps_search ', "")
                user['messages'] = [{**msg, 'content': get_decrypted_message(msg['content'], hashed_secret_key)} for msg in user['messages']]
                updatedDateString = user['updatedDateString']
                updatedDate = user['updatedDateString'].astimezone(jst)
                
                if (nowDate - updatedDate) > timedelta(days=1):
                    dailyUsage = 0
            else:
                user = {
                    'userId': userId,
                    'messages': [],
                    'updatedDateString': nowDate,
                    'dailyUsage': 0
                }
            if userMessage.strip() == f"😱{BOT_NAME}の記憶を消去":
                user['messages'] = []
                user['updatedDateString'] = nowDate
                callLineApi(FORGET_MESSAGE, replyToken, "")
                transaction.set(doc_ref, {**user, 'messages': []})
                return 'OK'
            elif message_type == 'image':
                exec_functions = True
                image_url = 'https://api-data.line.me/v2/bot/message/' + message_id + '/content'
                image = get_image(image_url, LINE_ACCESS_TOKEN) 
                vision_results = analyze_image(image)
                vision_results = vision_results_to_string(vision_results)
                headMessage = str(vision_results)
                userMessage = OCR_MESSAGE
            elif message_type == 'audio':
                exec_functions = True
                exec_audio = True
                image_url = 'https://api-data.line.me/v2/bot/message/' + message_id + '/content'
                image = get_image(image_url, LINE_ACCESS_TOKEN) 
                userMessage = "マイクのテスト中"
            elif message_type == 'sticker':
                keywords = event.get('message', {}).get('keywords', "")
                if keywords == "":
                    userMessage = FAIL_STICKER_MESSAGE
                else:
                    userMessage = STICKER_MESSAGE + "\n" + ', '.join(keywords)
            elif message_type == 'location':
                exec_functions = True 
                latitude =  event.get('message', {}).get('latitude', "")
                longitude = event.get('message', {}).get('longitude', "")
                result = maps_search(latitude, longitude, maps_search)
                headMessage = result['message']
                links = result['links']
                userMessage = MAPS_MESSAGE
                maps_search = ""
            elif "🌐インターネットで「" in userMessage:
                exec_functions = True
                searchwords = remove_specific_character(userMessage, '」を検索')
                searchwords = remove_specific_character(searchwords, '🌐インターネットで「')
                searchwords = remove_specific_character(searchwords, BOT_NAME)
                searchwords = replace_hiragana_with_spaces(searchwords)
                searchwords = searchwords.strip()
                result = search(searchwords)
                headMessage = result['searchwords']
                links = result['links']
                links = "\n❗参考\n" + "\n".join(links)
                
            if any(word in userMessage for word in SEARCH_KEYWORDS) and exec_functions == False:
                be_quick_reply = remove_specific_character(userMessage, SEARCH_KEYWORDS)
                be_quick_reply = replace_hiragana_with_spaces(be_quick_reply)
                be_quick_reply = be_quick_reply.strip() 
                be_quick_reply = "🌐インターネットで「" + be_quick_reply + "」を検索"
                be_quick_reply = create_quick_reply(be_quick_reply)
                quick_reply.append(be_quick_reply)
                headMessage = SEARCH_GUIDE_MESSAGE
            
            if any(word in userMessage for word in MAPS_KEYWORDS) and exec_functions == False:
                userMessage = remove_specific_character(userMessage, SEARCH_KEYWORDS)
                maps_search = remove_specific_character(userMessage, MAPS_FILTER_KEYWORDS)
                maps_search = replace_hiragana_with_spaces(maps_search)
                maps_search = maps_search.strip()
                be_quick_reply = "🗺️地図で検索"
                be_quick_reply = create_quick_reply(be_quick_reply)
                quick_reply.append(be_quick_reply)
                headMessage = MAPS_GUIDE_MESSAGE
            
            if any(word in userMessage for word in FORGET_KEYWORDS) and exec_functions == False:
                be_quick_reply = f"😱{BOT_NAME}の記憶を消去"
                be_quick_reply = create_quick_reply(be_quick_reply)
                quick_reply.append(be_quick_reply)
                headMessage = FORGET_GUIDE_MESSAGE
            if len(quick_reply) == 0:
                quick_reply = ""
                
            if any(word in userMessage for word in NG_KEYWORDS):
                headMessage = NG_MESSAGE 
            
            elif MAX_DAILY_USAGE is not None and dailyUsage is not None and MAX_DAILY_USAGE <= dailyUsage:
                callLineApi(countMaxMessage, replyToken, {'items': quick_reply})
                return 'OK'
            
            if sourceType == "group" or sourceType == "room":
                if BOT_NAME in userMessage or exec_functions == True:
                    pass
                else:
                    user['messages'].append({'role': 'user', 'content': display_name + ":" + userMessage})
                    transaction.set(doc_ref, {**user, 'messages': [{**msg, 'content': get_encrypted_message(msg['content'], hashed_secret_key)} for msg in user['messages']]})
                    return 'OK'
                
            temp_messages = nowDateStr + " " + act_as + headMessage + "\n" + display_name + ":" + userMessage
            total_chars = len(encoding.encode(SYSTEM_PROMPT)) + len(encoding.encode(temp_messages)) + sum([len(encoding.encode(msg['content'])) for msg in user['messages']])
            while total_chars > MAX_TOKEN_NUM and len(user['messages']) > 0:
                user['messages'].pop(0)
                total_chars = len(encoding.encode(SYSTEM_PROMPT)) + len(encoding.encode(temp_messages)) + sum([len(encoding.encode(msg['content'])) for msg in user['messages']])
                
            temp_messages_final = user['messages'].copy()
            temp_messages_final.append({'role': 'user', 'content': temp_messages}) 

            messages = user['messages']

            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={'Authorization': f'Bearer {OPENAI_APIKEY}'},
                json={'model': GPT_MODEL, 'messages': [systemRole()] + temp_messages_final},
                timeout=30 
            )
            
            user['messages'].append({'role': 'user', 'content': headMessage + "\n" + display_name + ":" + userMessage})

            response_json = response.json()

            if response.status_code != 200 or 'error' in response_json:
                print(f"OpenAI error: {response_json.get('error', 'No response from API')}")
                callLineApi(ERROR_MESSAGE, replyToken, {'items': quick_reply})
                return 'OK' 

            botReply = response_json['choices'][0]['message']['content'].strip()
            
            date_pattern = r"^\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2} [A-Z]{3,4}"
            botReply = re.sub(date_pattern, "", botReply).strip()

            user['messages'].append({'role': 'assistant', 'content': botReply})
            user['updatedDateString'] = nowDate
            user['dailyUsage'] += 1
            user['maps_search'] = maps_search
            transaction.set(doc_ref, {**user, 'messages': [{**msg, 'content': get_encrypted_message(msg['content'], hashed_secret_key)} for msg in user['messages']]})
            
            botReply = botReply + links
            
            if exec_audio == True:
                return 'OK'

            callLineApi(botReply, replyToken, {'items': quick_reply})
            return 'OK'

        return update_in_transaction(db.transaction(), doc_ref)
    except KeyError:
        return 'Not a valid JSON', 200 
    except Exception as e:
        print(f"Error in lineBot: {e}")
        callLineApi(ERROR_MESSAGE, replyToken, {'items': quick_reply})
        raise
    finally:
        return 'OK'

def get_profile(userId):
    url = 'https://api.line.me/v2/bot/profile/' + userId
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Authorization": "Bearer " + LINE_ACCESS_TOKEN,
    }
    response = requests.get(url, headers=headers, timeout=5)  # Timeout after 5 seconds
    return response

def create_quick_reply(quick_reply):
    if '🌐インターネットで「' in quick_reply:
        return {
            "type": "action",
            "action": {
                "type": "message",
                "label": '🌐インターネットで検索',
                "text": quick_reply
            }
        }
    elif f'😱{BOT_NAME}の記憶を消去' in quick_reply:
        return {
            "type": "action",
            "action": {
                "type": "message",
                "label": f'😱{BOT_NAME}の記憶を消去',
                "text": quick_reply
            }
        }
    elif '🗺️地図で検索' in quick_reply:
        return {
            "type": "action",
            "action": {
                "type": "location",
                "label": '🗺️地図で検索',
            }
        }

# ひらがなと句読点を削除
def replace_hiragana_with_spaces(text):
    hiragana_regex = r'[\u3040-\u309F。、！～？]'
    return re.sub(hiragana_regex, ' ', text)

# 特定文字削除
def remove_specific_character(text, characters_to_remove):
    for char in characters_to_remove:
        text = text.replace(char, '')
    return text

app.register_blueprint(vision, url_prefix='/vision')

@app.route("/search-form", methods=["GET", "POST"])
def search_form():
    if request.method == 'POST':
        question = request.form.get('question')
        results = search(question)
        return render_template('search-results.html', results=results)
    return render_template('search-form.html')

@app.route("/search-api", methods=["POST"])
def search_api():
    data = request.get_json()
    if not data or "question" not in data:
        return jsonify({"error": "Missing 'question' parameter"}), 400
    search_result = search(data["question"])
    return jsonify(search_result)

def search(question):
    search_result = get_search_results(question, 3)

    links = [item["link"] for item in search_result.get("items", [])]
    contents = get_contents(links)
    summary = summarize_contents(contents, question)

    if not summary:
        summary = FAIL_SEARCH_MESSAGE

    return {
        "searchwords": SEARCH_MESSAGE + "\n" + summary,
        "links": links
    }

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
