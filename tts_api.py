import os
print("Starting tts_api.py...")
import subprocess
import tempfile
from flask import Flask, request, send_file, abort, after_this_request

import logging

logging.basicConfig(filename='api.log', level=logging.DEBUG)

app = Flask(__name__)

VOICE_API_KEY = os.environ.get("VOICE_API_KEY")
if not VOICE_API_KEY:
    print("Error: VOICE_API_KEY environment variable not set. Please set it to your desired API key.")
    exit(1)
VOICE_MODEL_PATH = r"voices/en_US-amy-medium.onnx" 

@app.route("/synthesize", methods=["POST"])
def synthesize():
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {VOICE_API_KEY}":
        abort(401, "Unauthorized")

    data = request.get_json(force=True)
    text = data.get("text", "")
    if not text:
        abort(400, "Missing 'text' in request")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_file:
        wav_path = wav_file.name

    app.logger.info("Using VOICE_MODEL_PATH: %s", VOICE_MODEL_PATH)
    command = [
        "piper",
        "--model", VOICE_MODEL_PATH,
        "--text", text,
        "--output-file", wav_path
    ]

    result = subprocess.run(command, capture_output=True)
    app.logger.info("Piper stdout: %s", result.stdout.decode())
    app.logger.error("Piper stderr: %s", result.stderr.decode())

    if result.returncode != 0:
        abort(500, f"Piper error: {result.stderr.decode()}")

    try:
        response = send_file(wav_path, mimetype="audio/wav", as_attachment=True, download_name="output.wav")

        @after_this_request
        def remove_file(response):
            try:
                os.remove(wav_path)
            except Exception as e:
                app.logger.error("Error removing temporary file: %s", e)
            return response

        return response
    except Exception as e:
        app.logger.error("Error sending file or removing temporary file: %s", e)
        abort(500, "Error processing request")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)