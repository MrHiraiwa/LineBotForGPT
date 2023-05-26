import requests
import os
import json
import uuid

def get_audio(audio_url, line_access_token):
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Authorization": f"Bearer {line_access_token}",
    }
    response = requests.get(audio_url, headers=headers)
    return response.content

def speechToText(audio_bytes, OPENAI_APIKEY):
    try:
        # Generate a unique file name for each audio file
        filename = f"temp_audio_file_{uuid.uuid4()}.m4a"
        
        with open(filename, "wb") as f:
            f.write(audio_bytes)

        # Upload the file to the Whisper API
        with open(filename, 'rb') as f:
            formData = {
                'model': 'whisper',
                "temperature" : 0,
                'language': 'ja',
                'file': (filename, f, 'audio/m4a')
            }

            headers = {
                'Authorization': f'Bearer {OPENAI_APIKEY}'
            }

            response = requests.post('https://api.openai.com/v1/audio/transcriptions', headers=headers, files=formData)

        # Delete the temporary file
        os.remove(filename)

        response_json = response.json()
        text = response_json.get('text', '')
        return text
    except Exception as error:
        print(str(error))
        return ''
