import os
from tempfile import NamedTemporaryFile
import requests
from google.cloud import texttospeech, storage
import subprocess
from pydub.utils import mediainfo
import langid

LINE_ACCESS_TOKEN = os.getenv('LINE_ACCESS_TOKEN')


def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        blob.upload_from_filename(source_file_name)
    
        # Construct public url
        public_url = f"https://storage.googleapis.com/{bucket_name}/{destination_blob_name}"
        #print(f"Successfully uploaded file to {public_url}")
        return public_url
    except Exception as e:
        print(f"Failed to upload file: {e}")
        raise
        
def convert_audio_to_m4a(input_path, output_path):
    command = ['ffmpeg', '-i', input_path, '-c:a', 'aac', output_path]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    #print("stdout:", result.stdout)
    #print("stderr:", result.stderr)

def text_to_speech(text, bucket_name, destination_blob_name, mandarin_or_cantonese):
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    
    detected_lang, dialect = detect_language(text)

    if detected_lang == 'ja':
        language_code = "ja-JP"
        ssml_gender = texttospeech.SsmlVoiceGender.FEMALE
    elif detected_lang == 'en':
        language_code = "en-US"
        ssml_gender = texttospeech.SsmlVoiceGender.FEMALE
    elif detected_lang == 'zh' and mandarin_or_cantonese == 'MANDARIN':
        language_code = "zh-CN"
        ssml_gender = texttospeech.SsmlVoiceGender.FEMALE
    elif detected_lang == 'zh' and mandarin_or_cantonese == 'CANTONESE':
        language_code = "yue-Hant-HK"
        ssml_gender = texttospeech.SsmlVoiceGender.FEMALE
    elif detected_lang == 'ko':
        language_code = "ko-KR"
        ssml_gender = texttospeech.SsmlVoiceGender.FEMALE
    elif detected_lang == 'id':
        language_code = "id-ID"
        ssml_gender = texttospeech.SsmlVoiceGender.FEMALE
    elif detected_lang == 'th':
        language_code = "th-TH"
        ssml_gender = texttospeech.SsmlVoiceGender.FEMALE
    else:
        language_code = "ja-JP"  # Default to Japanese if language detection fails
        ssml_gender = texttospeech.SsmlVoiceGender.FEMALE
        
    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        ssml_gender=ssml_gender
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

        # Get the duration of the local file before uploading
        duration = get_duration(m4a_path)

        # Upload the m4a file
        public_url = upload_blob(bucket_name, m4a_path, destination_blob_name)
        
        # Return the public url, local path of the file, and duration
        return public_url, m4a_path, duration

def send_audio_to_line(audio_path, user_id, duration):
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
                "duration": duration
            }
        ]
    }
    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        #print(f"Audio successfully sent to user {user_id}")
        return True
    else:
        print(f"Failed to send audio: {response.content}")
        return False
    
def send_audio_to_line_reply(audio_path, reply_token, duration):
    url = 'https://api.line.me/v2/bot/message/reply'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_ACCESS_TOKEN}'
    }

    data = {
        "replyToken": reply_token,
        "messages":[
            {
                "type":"audio",
                "originalContentUrl": audio_path,
                "duration": duration
            }
        ]
    }
    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        #print(f"Audio successfully sent to user {user_id}")
        return True
    else:
        print(f"Failed to send audio: {response.content}")
        return False

    
    
def delete_local_file(file_path):
    """Deletes a local file."""
    if os.path.isfile(file_path):
        os.remove(file_path)
        #print(f"Local file {file_path} deleted.")
    #else:
        #print(f"No local file found at {file_path}.")    

def delete_blob(bucket_name, blob_name):
    """Deletes a blob from the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.delete()
    #print(f"Blob {blob_name} deleted.")
    
def get_duration(file_path):
    info = mediainfo(file_path)
    #print(f"mediainfo: {info}")
    duration = info.get('duration')  # durationの値がない場合はNoneを返す
    if duration is None:
        print(f"No duration information found for {file_path}.")
        return 0  # または適当なデフォルト値
    else:
        return int(float(duration)) * 1000  # Convert to milliseconds

def detect_language(text):
    try:
        lang, dialect = langid.classify(text)
        return lang, dialect
    except:
        return None, None
    
from google.cloud import storage

def set_bucket_lifecycle(bucket_name, age):
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)

    rule = {
        'action': {'type': 'Delete'},
        'condition': {'age': age}  # The number of days after object creation
    }
    
    bucket.lifecycle_rules = [rule]
    bucket.patch()

    #print(f"Lifecycle rule set for bucket {bucket_name}.")
