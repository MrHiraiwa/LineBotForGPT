import requests
import os
import json

def get_audio(audio_url, line_access_token):
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Authorization": f"Bearer {line_access_token}",
    }
    response = requests.get(audio_url, headers=headers)
    return response.content

def speechToText(audio_bytes, OPENAI_APIKEY):
    try:
        with open("temp_audio_file.m4a", "wb") as f:
            f.write(audio_bytes)

        # Upload the file to the Whisper API
        with open("temp_audio_file.m4a", 'rb') as f:
            formData = {
                'model': 'whisper',
                "temperature" : 0,
                'language': 'ja',
                'file': ('temp_audio_file.m4a', f, 'audio/m4a')
            }

            headers = {
                'Authorization': f'Bearer {OPENAI_APIKEY}'
            }

            response = requests.post('https://api.openai.com/v1/audio/transcriptions', headers=headers, files=formData)

        # Delete the temporary file
        os.remove("temp_audio_file.m4a")

        response_json = response.json()
        text = response_json.get('text', '')
        return text
    except Exception as error:
        print(str(error))
        return ''

