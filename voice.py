import os
from tempfile import NamedTemporaryFile
import requests
from google.cloud import texttospeech, storage
import subprocess
from pydub.utils import mediainfo

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
        print(f"Successfully uploaded file to {public_url}")
        return public_url
    except Exception as e:
        print(f"Failed to upload file: {e}")
        raise

  def convert_audio_to_m4a(input_path, output_path):
    command = ['ffmpeg', '-i', input_path, output_path]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    print("stdout:", result.stdout)
    print("stderr:", result.stderr)

def text_to_speech(text, bucket_name, destination_blob_name):
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="ja-JP",
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

        # Return the local path of the file
    return m4a_path

# Then, in your send_audio_to_line function:

def send_audio_to_line(audio_path, user_id, bucket_name, blob_path):
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_ACCESS_TOKEN}'
    }

    # Get the duration of the local file before uploading
    duration = get_duration(audio_path)

    # Now upload the blob
    public_url = upload_blob(bucket_name, audio_path, blob_path)

    data = {
        "to": user_id,
        "messages":[
            {
                "type":"audio",
                "originalContentUrl": public_url,
                "duration": duration
            }
        ]
    }
    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        delete_blob(bucket_name, blob_path)
        return True
    else:
        print(f"Failed to send audio: {response.content}")
        return False

def delete_blob(bucket_name, blob_name):
    """Deletes a blob from the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.delete()
    print(f"Blob {blob_name} deleted.")
    
def get_duration(file_path):
    info = mediainfo(file_path)
    print(f"mediainfo: {info}")
    duration = info.get('duration')  # durationの値がない場合はNoneを返す
    if duration is None:
        print(f"No duration information found for {file_path}.")
        return 0  # または適当なデフォルト値
    else:
        return int(float(duration)) * 1000  # Convert to milliseconds

