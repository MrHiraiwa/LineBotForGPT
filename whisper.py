import requests
import json
import os
from io import BytesIO

# Environment variables should be used to securely store the API keys
OPENAI_APIKEY = os.getenv('OPENAI_APIKEY')
LINE_ACCESS_TOKEN = os.getenv('LINE_ACCESS_TOKEN')

def speech_to_text(file):
    payload = {
        'model': 'whisper-1',
        'temperature': 0,
        'file': file
    }

    headers = {
        'Authorization': f'Bearer {OPENAI_APIKEY}'
    }

    response = requests.post(
        "https://api.openai.com/v1/audio/transcriptions", 
        headers=headers, 
        files=payload
    )

    if response.status_code == 200:
        return response.json().get('text')
    else:
        return response.content

def get_audio(message_id):
    url = f'https://api-data.line.me/v2/bot/message/{message_id}/content'

    headers = {
        'Authorization': f'Bearer {LINE_ACCESS_TOKEN}',
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        # Create a temporary file in memory
        temp = BytesIO(response.content)

        # Call the speech_to_text function with the temporary file
        return speech_to_text(temp)
