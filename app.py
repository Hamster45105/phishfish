"""
Flask web app for phishing email detection.
"""
import os
import tempfile
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

from phishing_detector import parse_email, format_email, classify_email
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential

# Load .env file for environment variables
load_dotenv()

app = Flask(__name__)

# Initialize Azure AI client
endpoint = "https://models.github.ai/inference"
model = "openai/gpt-4.1"
token = os.environ.get("GITHUB_TOKEN")
if not token:
    raise RuntimeError("GITHUB_TOKEN env var is required")
client = ChatCompletionsClient(endpoint=endpoint, credential=AzureKeyCredential(token))

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'email_file' not in request.files:
            return render_template('index.html', error='No file part')
        file = request.files['email_file']
        if file.filename == '':
            return render_template('index.html', error='No selected file')
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.eml') as tmp:
            tmp.write(file.read())
            tmp_path = tmp.name
        # Parse and classify
        metadata, body, urls = parse_email(tmp_path)
        preview = format_email(metadata, body, urls)
        result_text = classify_email(preview, client, model)
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        # Parse result into components
        lines = result_text.strip().splitlines()
        data = {}
        for line in lines:
            if ': ' in line:
                key, val = line.split(': ', 1)
                data[key.lower()] = val
        return render_template('result.html', preview=preview, **data)
    return render_template('index.html')

@app.route('/preview', methods=['POST'])
def preview():
    """Return the formatted email content for preview."""
    if 'email_file' not in request.files:
        return jsonify(error='No file part'), 400
    file = request.files['email_file']
    if file.filename == '':
        return jsonify(error='No selected file'), 400
    # Save to temp and parse
    with tempfile.NamedTemporaryFile(delete=False, suffix='.eml') as tmp:
        tmp.write(file.read())
        tmp_path = tmp.name
    metadata, body, urls = parse_email(tmp_path)
    preview_text = format_email(metadata, body, urls)
    try:
        os.unlink(tmp_path)
    except OSError:
        pass
    return jsonify(preview=preview_text)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
