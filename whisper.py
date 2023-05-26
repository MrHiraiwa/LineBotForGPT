import requests
import json
import os
from io import BytesIO

# Environment variables should be used to securely store the API keys
OPENAI_APIKEY = os.getenv('OPENAI_APIKEY')
LINE_ACCESS_TOKEN = os.getenv('LINE_ACCESS_TOKEN')

def get_audio(message_id):
    url = f'https://api-data.line.me/v2/bot/message/{message_id}/content'

    headers = {
        'Authorization': f'Bearer {LINE_ACCESS_TOKEN}',
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        # Save the audio file temporarily
        with NamedTemporaryFile(suffix=".m4a", delete=False) as temp:
            temp.write(response.content)
            temp.flush()

        # Call the speech_to_text function with the temporary file
        return speech_to_text(temp.name)
    else:
        print(f"Failed to fetch audio: {response.content}")
        return None

def speech_to_text(file_path):
    with open(file_path, 'rb') as f:
        payload = {
            'model': 'whisper-1',
            'temperature': 0
        }

        headers = {
            'Authorization': f'Bearer {OPENAI_APIKEY}'
        }

        files = {
            'file': (os.path.basename(file_path), f)
        }

        response = requests.post(
            "https://api.openai.com/v1/audio/transcriptions", 
            headers=headers, 
            data=payload, 
            files=files
        )

        if response.status_code == 200:
            return response.json().get('text')
        else:
            print(f"Failed to transcribe audio: {response.content}")
            return None
