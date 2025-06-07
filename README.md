# HookSnare Phishing Detector

This Flask web application lets you upload raw email files (`.eml`) and uses Azure AI to classify them as legitimate, phishing, or unsure.

## Installation

1. Clone or download this repository.
2. Change into the project directory:
   ```bash
   cd HookSnare
   ```
3. (Optional) Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source venv/bin/activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Set the following environment variables in your shell (e.g., `zsh`):

```bash
export GITHUB_TOKEN="<your-azure-token>"
```

Ensure `GITHUB_TOKEN` points to an Azure OpenAI or GitHub AI inference credential that has Chat Completions access.

## Running the App

Start the Flask server:
```bash
python app.py
```

By default it runs on `http://0.0.0.0:5000`. Open your browser and navigate to `http://localhost:5000`.