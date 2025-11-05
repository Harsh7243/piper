import os
import subprocess
import tempfile
from flask import Flask, request, jsonify, abort
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

app = Flask(__name__)

VOICE_API_KEY = os.environ.get("VOICE_API_KEY")
GOOGLE_DRIVE_FOLDER_ID = os.environ.get("GOOGLE_DRIVE_FOLDER_ID")
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_credentials():
    cred = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if cred and cred.strip().startswith('{'):
        cred_path = "/tmp/service_account.json"
        with open(cred_path, "w") as f:
            f.write(cred)
        return service_account.Credentials.from_service_account_file(cred_path, scopes=SCOPES)
    else:
        return service_account.Credentials.from_service_account_file(cred, scopes=SCOPES)

@app.route("/api/synthesize", methods=["POST"])
def synthesize():
    if VOICE_API_KEY is None:
        abort(500, "Server misconfiguration: VOICE_API_KEY not set.")
    if GOOGLE_DRIVE_FOLDER_ID is None:
        abort(500, "Server misconfiguration: GOOGLE_DRIVE_FOLDER_ID not set.")

    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {VOICE_API_KEY}":
        abort(401, "Unauthorized")

    data = request.get_json(force=True)
    text = data.get("text", "")
    if not text:
        abort(400, "Missing 'text' in request")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_file:
        wav_path = wav_file.name

    command = [
        "piper",
        "--model", "voices/en_US-amy-medium.onnx",
        "--text", text,
        "--output-file", wav_path
    ]

    result = subprocess.run(command, capture_output=True)
    if result.returncode != 0:
        abort(500, f"Piper error: {result.stderr.decode()}")

    credentials = get_credentials()
    drive_service = build('drive', 'v3', credentials=credentials)
    file_metadata = {
        'name': os.path.basename(wav_path),
        'parents': [GOOGLE_DRIVE_FOLDER_ID]
    }
    media = MediaFileUpload(wav_path, mimetype='audio/wav')
    file = drive_service.files().create(
        body=file_metadata, media_body=media, fields='id,webViewLink'
    ).execute()
    os.remove(wav_path)
    return jsonify({"file_id": file.get('id'), "file_url": file.get('webViewLink')})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
