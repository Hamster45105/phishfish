"""
Email parsing functionality for PhishFish application.
"""

import re
from email.header import decode_header
from email.parser import BytesParser


def parse_email_bytes(raw_bytes):
    """Parse raw email bytes and return metadata, body, and URLs."""
    msg = BytesParser().parsebytes(raw_bytes)

    # Decode headers to handle encoded-words
    def decode_field(header_value):
        parts = decode_header(header_value or "")
        decoded = []
        for fragment, encoding in parts:
            if isinstance(fragment, bytes):
                decoded.append(fragment.decode(encoding or "utf-8", errors="replace"))
            else:
                decoded.append(fragment)
        return "".join(decoded)

    metadata = {
        "from": decode_field(msg["from"]),
        "to": decode_field(msg["to"]),
        "date": msg["date"] or "",
        "subject": decode_field(msg["subject"]),
    }

    # Decode text/plain parts, handling base64/quoted-printable
    body_parts = []
    for part in msg.walk():
        if part.get_content_type() == "text/plain" and not part.is_multipart():
            payload = part.get_payload(decode=True)
            charset = part.get_content_charset() or "utf-8"
            if isinstance(payload, (bytes, bytearray)):
                text = payload.decode(charset, errors="replace")
            else:
                text = str(payload)
            body_parts.append(text)

    body = "\n".join(body_parts)
    urls = re.findall(r"https?://[^\s\"']+", body)

    return metadata, body, urls


def format_email(metadata, body, urls):
    """Build a single string of key headers, URLs, and body for AI."""
    header_lines = [
        f"From: {metadata['from']}",
        f"To: {metadata['to']}",
        f"Date: {metadata['date']}",
        f"Subject: {metadata['subject']}",
    ]

    if urls:
        header_lines.append("URLs: " + ", ".join(urls))

    return "\n".join(header_lines) + "\n\nBody:\n" + body
