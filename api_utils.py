import requests

def callLineApi(replyText, replyToken, LINE_ACCESS_TOKEN):
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
