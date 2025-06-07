"""
Phishing email detector using Azure AI Inference.
"""
import re
from email.parser import BytesParser
from azure.ai.inference.models import SystemMessage, UserMessage

def parse_email(path):
    """Parse an .eml file and return key headers, body, and URLs."""
    with open(path, 'rb') as f:
        msg = BytesParser().parse(f)
    metadata = {
        'from': msg['from'] or "",
        'to': msg['to'] or "",
        'date': msg['date'] or "",
        'subject': msg['subject'] or ""
    }
    # Extract text/plain body with payload decoding
    if msg.is_multipart():
        parts = []
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                text = part.get_payload()
                if isinstance(text, str):
                    parts.append(text)
        body = '\n'.join(parts)
    else:
        text = msg.get_payload()
        body = text if isinstance(text, str) else ''
    # Find URLs in body
    urls = re.findall(r'https?://[^\s"\']+', body)
    return metadata, body, urls

def format_email(metadata, body, urls):
    """Build a single string of key headers, URLs, and body for AI."""
    header_lines = [f"From: {metadata['from']}", f"To: {metadata['to']}",
                    f"Date: {metadata['date']}", f"Subject: {metadata['subject']}"]
    if urls:
        header_lines.append("URLs: " + ", ".join(urls))
    return "\n".join(header_lines) + "\n\nBody:\n" + body

def classify_email(email_content, client, model):
    """Use Azure AI to classify the provided email content."""
    system_prompt = (
        "You are an assistant that classifies emails as legitimate, phishing, or unsure. "
        "Only use these three labels. Provide a one-sentence reason for your classification. "
        "If the classification is phishing or unsure, add a one-sentence advice on what the user should do next. "
        "Format the response exactly as:\n"
        "Classification: <label>\n"
        "Reason: <reason>\n"
        "Advice: <advice>"
    )
    response = client.complete(
        messages=[
            SystemMessage(system_prompt),
            UserMessage(email_content),
        ],
        temperature=0.0,
        top_p=1.0,
        model=model
    )
    return response.choices[0].message.content
