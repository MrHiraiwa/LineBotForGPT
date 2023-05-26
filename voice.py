import os
from tempfile import NamedTemporaryFile
import requests
from google.cloud import texttospeech
import subprocess

def convert_audio_to_m4a(input_path, output_path):
    command = ['ffmpeg', '-i', input_path, output_path]
    subprocess.run(command, check=True)

# Then, in your text_to_speech function:

def text_to_speech(text):
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    # Save the audio file temporarily
    with NamedTemporaryFile(suffix=".mp3", delete=False) as temp:
        temp.write(response.audio_content)
        temp.flush()
        # Convert the MP3 file to M4A
        m4a_path = temp.name.replace(".mp3", ".m4a")
        convert_audio_to_m4a(temp.name, m4a_path)

    return m4a_path

def send_audio_to_line(audio_path, user_id):
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_ACCESS_TOKEN}'
    }
    data = {
        "to": user_id,
        "messages":[
            {
                "type":"audio",
                "originalContentUrl": audio_path,
                "duration": 240000
            }
        ]
    }
    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        return True
    else:
        print(f"Failed to send audio: {response.content}")
        return False
