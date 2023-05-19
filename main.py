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
    elif MAX_DAILY_USAGE and MAX_DAILY_USAGE <= dailyUsage:
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
    botReply = response.json()['choices'][0]['message']['content'].trim()

    # Save bot response after received
    user['messages'].append({'role': 'assistant', 'content': get_encrypted_message(botReply, hashed_secret_key)})
    user['updatedDateString'] = nowDate
    user['dailyUsage'] += 1

    doc_ref.set(user)

    callLineApi(botReply, replyToken)
    return 'OK', 200
