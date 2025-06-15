"""
Background job to poll emails via IMAP and notify users of phishing.
"""

from pathlib import Path
import logging
import time
import os
import json
import re
import sys
from datetime import datetime

from email.parser import BytesParser
from email.header import decode_header
import requests
from imapclient import IMAPClient
from imapclient.exceptions import LoginError
from dotenv import load_dotenv

from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

# Load .env file if it exists (for local development)
dotenv_path = Path(__file__).resolve().parent.parent / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path, override=True)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# IMAP settings
IMAP_HOST = os.environ['IMAP_HOST']
IMAP_USER = os.environ['IMAP_USER']
IMAP_PASS = os.environ['IMAP_PASS']
IMAP_PORT = int(os.getenv('IMAP_PORT', '993'))
IMAP_AUTH_METHOD = os.getenv('IMAP_AUTH_METHOD', 'SSL').upper()
MAILBOX = os.getenv('IMAP_MAILBOX', 'INBOX')

# NTFY settings
NTFY_TOPIC = os.environ['NTFY_TOPIC']
NTFY_URL = os.getenv('NTFY_URL', 'https://ntfy.sh')
NTFY_URL = f'{NTFY_URL}/{NTFY_TOPIC}'

NTFY_TITLE = os.getenv('NTFY_TITLE', 'PhishFish Email Report')
NOTIFY_ON = [c.strip().lower() for c in os.getenv('NOTIFY_ON', 'phishing').split(',')]

# Azure AI settings
token = os.environ['GITHUB_TOKEN']
model = os.getenv('AZURE_MODEL', 'openai/gpt-4.1')
endpoint = os.getenv('AZURE_ENDPOINT', 'https://models.github.ai/inference')
client = ChatCompletionsClient(endpoint=endpoint, credential=AzureKeyCredential(token))

def parse_email_bytes(raw_bytes):
    """Parse raw email bytes and return metadata, body, and URLs."""
    msg = BytesParser().parsebytes(raw_bytes)
    # Decode headers to handle encoded-words
    def decode_field(header_value):
        parts = decode_header(header_value or '')
        decoded = []
        for fragment, encoding in parts:
            if isinstance(fragment, bytes):
                decoded.append(fragment.decode(encoding or 'utf-8', errors='replace'))
            else:
                decoded.append(fragment)
        return ''.join(decoded)
    metadata = {
        'from': decode_field(msg['from']),
        'to': decode_field(msg['to']),
        'date': msg['date'] or '',
        'subject': decode_field(msg['subject'])
    }
    # Decode text/plain parts, handling base64/quoted-printable
    body_parts = []
    for part in msg.walk():
        if part.get_content_type() == 'text/plain' and not part.is_multipart():
            payload = part.get_payload(decode=True)
            charset = part.get_content_charset() or 'utf-8'
            if isinstance(payload, (bytes, bytearray)):
                text = payload.decode(charset, errors='replace')
            else:
                text = str(payload)
            body_parts.append(text)
    body = '\n'.join(body_parts)
    urls = re.findall(r"https?://[^\s\"']+", body)
    return metadata, body, urls

def format_email(metadata, body, urls):
    """Build a single string of key headers, URLs, and body for AI."""
    header_lines = [f"From: {metadata['from']}", f"To: {metadata['to']}",
                    f"Date: {metadata['date']}", f"Subject: {metadata['subject']}"]
    if urls:
        header_lines.append("URLs: " + ", ".join(urls))
    return "\n".join(header_lines) + "\n\nBody:\n" + body

def classify_email(email_content):
    """Use Azure AI to classify the email and return JSON result."""
    system_prompt = (
        "You are an assistant that classifies emails as legitimate or phishing. "
        "Only use these two labels. Scam emails are counted as phishing. Provide a one-sentence reason. "
        "Your job is not to determine if the email is a legitimate marketing email. "
        "If phishing/scam, include one-sentence advice. "
        "In most cases, advice should be simple, eg: Ignore the email, delete it, or do not click any links. "
        "Only provide additional advice if you think it is necessary. "
        "Respond with a JSON object with keys 'classification', 'reason', and 'advice'. "
        "Do not output any additional text."
    )
    # Call Azure AI and handle errors
    try:
        response = client.complete(
            messages=[SystemMessage(system_prompt), UserMessage(email_content)],
            temperature=0.0, top_p=1.0, model=model
        )
    except Exception as e:
        raise RuntimeError(f"AI classification failed: {e}") from e
    content = response.choices[0].message.content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError as je:
        raise RuntimeError(f"Invalid JSON from AI: {je}\nContent was: {content}") from je

def notify_user(sender, subject, result):
    """Send a notification via ntfy.sh"""

    # Sanitize subject for headers (no CR/LF)
    clean_subject = subject.replace('\r', ' ').replace('\n', ' ').strip()

    # Use preloaded ntfy settings
    topic = NTFY_TOPIC
    ntfy_url = NTFY_URL

    # result is a dict from classify_email
    cls = result.get('classification','').lower()
    # Skip notifications if not in filter
    if cls not in NOTIFY_ON:
        logging.info("Skipping notification for classification '%s'", cls)
        return
    reason = result.get('reason','')
    advice = result.get('advice','')

    # Choose emoji based on classification
    emoji = '🔴' if 'phish' in cls else '🟢'

    # Build message parts
    parts = [
        f"SENDER: \"{sender}\"",
        f"SUBJECT: \"{clean_subject}\"",
        f"CLASSIFICATION: {emoji} {cls}",
        f"REASON: {reason}",
    ]
    if advice:
        parts.append(f"ADVICE: {advice}")
    # Use double line breaks for separation
    message = '\n\n'.join(parts)

    # Set ntfy.sh headers
    headers = {
        'Title': NTFY_TITLE,
    }

    try:
        resp = requests.post(ntfy_url, data=message.encode('utf-8'), headers=headers, timeout=5)
        resp.raise_for_status()
        logging.info("Sent ntfy notification for '%s' to topic '%s'", subject, topic)
    except Exception as e:
        logging.error("Failed to send ntfy notification: %s", e)

def process_single_email(imap_client, uid):
    """Process a single email UID - fetch, classify, and notify."""
    try:
        # Fetch email data with error handling for missing UIDs
        fetch_result = imap_client.fetch(uid, ['BODY.PEEK[]'])
        
        data = fetch_result[uid]
        raw = data.get(b'BODY[]')
        if not isinstance(raw, (bytes, bytearray)):
            logging.warning("Skipping UID %s: invalid format", uid)
            # Only try to flag if the UID still exists
            imap_client.add_flags(uid, 'StopThePhish_Processed')
            return

        metadata, body, urls = parse_email_bytes(raw)
        preview = format_email(metadata, body, urls)
        logging.info("Email UID %s sent to AI for classification", uid)

        result = classify_email(preview)
        logging.info("UID %s classified as '%s'", uid, result.get('classification',''))

        notify_user(metadata['from'], metadata['subject'], result)

        # Mark as processed (but keep unread if legitimate)
        try:
            imap_client.add_flags(uid, 'StopThePhish_Processed')
            # Verify the flag was set
            flags_data = imap_client.fetch(uid, ['FLAGS'])[uid]
            current_flags = flags_data.get(b'FLAGS', [])
            logging.info("UID %s processed and flagged: %s", uid, current_flags)
        except Exception as e:
            logging.warning("Could not flag UID %s as processed: %s - email may no longer exist", uid, e)

    except Exception as e:
        logging.error("Error processing email UID %s: %s", uid, str(e))
        logging.error("Exception type: %s", type(e).__name__)
        import traceback
        logging.error("Traceback: %s", traceback.format_exc())
        # Still mark as processed to avoid reprocessing failures
        try:
            imap_client.add_flags(uid, 'StopThePhish_Processed')
        except Exception as flag_error:
            logging.warning("Could not flag UID %s as processed after error: %s - email may no longer exist", uid, flag_error)

def process_unseen(client_imap):
    """Find all UNSEEN and unprocessed messages and process them immediately."""
    uids = client_imap.search(['UNSEEN', 'NOT', 'KEYWORD', 'StopThePhish_Processed'])
    logging.info("Found %d unseen, unprocessed messages in '%s'", len(uids), MAILBOX)
    for uid in uids:
        process_single_email(client_imap, uid)

if __name__ == '__main__':
    def monitor_mailbox_idle():
        """Connect once, then enter IMAP IDLE to process new mail immediately."""
        logging.info('Starting IMAP IDLE monitor')
        try:
            # Establish main IMAP connection for IDLE
            logging.info("Connecting to IMAP %s:%d using %s", IMAP_HOST, IMAP_PORT, IMAP_AUTH_METHOD)
            if IMAP_AUTH_METHOD == 'SSL':
                imap_client = IMAPClient(IMAP_HOST, port=IMAP_PORT, ssl=True)
            elif IMAP_AUTH_METHOD == 'STARTTLS':
                imap_client = IMAPClient(IMAP_HOST, port=IMAP_PORT, ssl=False)
                imap_client.starttls()
            else:
                imap_client = IMAPClient(IMAP_HOST, port=IMAP_PORT, ssl=False)
            imap_client.login(IMAP_USER, IMAP_PASS)
            imap_client.select_folder(MAILBOX)
            logging.info("Authenticated – entering IDLE")

            process_unseen(imap_client)

        except LoginError as e:
            logging.error("IMAP login failed: %s", e)
            sys.exit(1)
        except Exception as e:
            logging.error("Failed to initialize: %s", e)
            sys.exit(1)

        # Main IDLE loop with exponential back-off
        backoff = 5
        max_backoff = 300

        try:
            while True:
                try:
                    logging.info("Entering IMAP IDLE")
                    imap_client.idle()
                    responses = imap_client.idle_check(timeout=300)
                    imap_client.idle_done()
                    logging.info("IDLE returned responses: %s", responses)

                    for resp in responses:
                        if isinstance(resp, tuple) and len(resp) > 1 and resp[1] == b'EXISTS':
                            logging.info('New email detected; processing immediately')
                            process_unseen(imap_client)
                            break

                except Exception as e:
                    logging.error("Error in IDLE loop: %s; backing off %ds", e, backoff)
                    time.sleep(backoff)
                    backoff = min(backoff * 2, max_backoff)
        except KeyboardInterrupt:
            logging.info("Received interrupt signal, shutting down...")

    monitor_mailbox_idle()
