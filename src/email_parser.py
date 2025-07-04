"""
Email parsing functionality for PhishFish application.
"""

import re
from email.header import decode_header
from email.parser import BytesParser

from config import config


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


def extract_email_address(sender_field):
    """Extract email address from sender field like 'Name <email@domain.com>' or just 'email@domain.com'."""
    if not sender_field:
        return ""

    # Try to match email in angle brackets first
    match = re.search(r"<([^>]+)>", sender_field)
    if match:
        return match.group(1).strip().lower()

    # If no angle brackets, assume the whole string is the email
    # Remove any extra whitespace and convert to lowercase
    return sender_field.strip().lower()


def extract_domain(email_address):
    """Extract domain from email address."""
    if not email_address or "@" not in email_address:
        return ""
    return email_address.split("@")[1].lower()


def check_sender_classification(sender_field):
    """
    Check if sender is in dangerous or safe lists.
    Conflict resolution rules:
    - If exact same entry in both lists: dangerous takes precedence (with warning)
    - If different match types (email vs domain): specific email takes precedence over domain
    Returns tuple: (classification, reason) or (None, None) if not found.
    """
    if not sender_field:
        return None, None

    email_address = extract_email_address(sender_field)
    domain = extract_domain(email_address)

    # Check for matches in both lists
    dangerous_match = None
    dangerous_match_type = None
    safe_match = None
    safe_match_type = None

    # Check dangerous senders
    for dangerous_sender in config.DANGEROUS_SENDERS:
        if dangerous_sender.startswith("@"):
            # Domain match
            if domain == dangerous_sender[1:]:
                dangerous_match = (
                    "phishing",
                    f"Sender domain '{domain}' is in the dangerous list",
                )
                dangerous_match_type = "domain"
                break
        else:
            # Exact email match
            if email_address == dangerous_sender:
                dangerous_match = (
                    "phishing",
                    f"Sender '{email_address}' is in the dangerous list",
                )
                dangerous_match_type = "email"
                break

    # Check safe senders
    for safe_sender in config.SAFE_SENDERS:
        if safe_sender.startswith("@"):
            # Domain match
            if domain == safe_sender[1:]:
                safe_match = (
                    "legitimate",
                    f"Sender domain '{domain}' is in the safe list",
                )
                safe_match_type = "domain"
                break
        else:
            # Exact email match
            if email_address == safe_sender:
                safe_match = (
                    "legitimate",
                    f"Sender '{email_address}' is in the safe list",
                )
                safe_match_type = "email"
                break

    # Handle conflicts
    if dangerous_match and safe_match:
        import logging

        # Check if it's the same type of match (both email or both domain)
        if dangerous_match_type == safe_match_type:
            # Exact same entry in both lists - dangerous takes precedence
            if dangerous_match_type == "email":
                logging.warning(
                    "Sender conflict detected: Email '%s' is in both dangerous and safe lists. "
                    "Dangerous takes precedence.",
                    email_address,
                )
            else:  # domain
                logging.warning(
                    "Sender conflict detected: Domain '%s' is in both dangerous and safe lists. "
                    "Dangerous takes precedence.",
                    domain,
                )
            return dangerous_match
        else:
            # Different match types - email takes precedence over domain
            if dangerous_match_type == "email":
                logging.warning(
                    "Sender conflict detected: Email '%s' is in dangerous list and domain '%s' is in safe list. "
                    "Specific email takes precedence - classifying as dangerous.",
                    email_address,
                    domain,
                )
                return dangerous_match
            else:  # safe_match_type == "email"
                logging.warning(
                    "Sender conflict detected: Email '%s' is in safe list and domain '%s' is in dangerous list. "
                    "Specific email takes precedence - classifying as safe.",
                    email_address,
                    domain,
                )
                return safe_match

    # Return whichever match was found (no conflict)
    if dangerous_match:
        return dangerous_match
    if safe_match:
        return safe_match

    return None, None
