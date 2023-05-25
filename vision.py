from flask import Blueprint, request, redirect, jsonify
import requests
import base64
import os

vision = Blueprint('vision', __name__)

GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')  # API key should be stored in environment variables

def analyze_image(image_bytes):
    api_url = "https://vision.googleapis.com/v1/images:annotate?key=" + GOOGLE_API_KEY
    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    request_body = {
        "requests": [
            {
                "image": {
                    "content": base64_image
                },
                "features": [
                    { "type": "LABEL_DETECTION" },
                    { "type": "TEXT_DETECTION" },
                    { "type": "LANDMARK_DETECTION" },
                    { "type": "FACE_DETECTION" },
                    { "type": "OBJECT_LOCALIZATION" },
                    { "type": "DOCUMENT_TEXT_DETECTION" }
                ]
            }
        ]
    }

    response = requests.post(api_url, json=request_body)
    return response.json()

import requests

def get_image(image_url, line_access_token):
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Authorization": f"Bearer {line_access_token}",
    }
    response = requests.get(image_url, headers=headers)
    return response.content


@vision.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            image_bytes = file.read()
            vision_results = analyze_image(image_bytes)
            result_string = str(vision_results)
            return jsonify(result=result_string)

    return '''
    <!doctype html>
    <title>Upload Image</title>
    <h1>Upload Image</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''

