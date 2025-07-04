"""
Notification functionality for PhishFish application.
"""

import logging

import requests

from config import config


def notify_user(sender, subject, result):
    """Send a notification via ntfy.sh"""

    if not config.NTFY_ENABLED:
        return

    # Sanitize subject for headers (no CR/LF)
    clean_subject = subject.replace("\r", " ").replace("\n", " ").strip()

    # result is a dict from classify_email
    cls = result.get("classification", "").lower()

    # Skip notifications if not in filter
    if cls not in config.NOTIFY_ON:
        logging.info("Skipping notification for classification '%s'", cls)
        return

    reason = result.get("reason", "")
    advice = result.get("advice", "")

    # Choose emoji based on classification
    emoji = "🔴" if "phish" in cls else "🟢"

    # Build message parts
    parts = [
        f'SENDER: "{sender}"',
        f'SUBJECT: "{clean_subject}"',
        f"CLASSIFICATION: {emoji} {cls}",
        f"REASON: {reason}",
    ]

    if advice and emoji == "🔴":
        parts.append(f"ADVICE: {advice}")

    # Use double line breaks for separation
    message = "\n\n".join(parts)

    # Set ntfy headers
    headers = {
        "Title": config.NTFY_TITLE,
    }

    try:
        resp = requests.post(
            config.ntfy_full_url,
            data=message.encode("utf-8"),
            headers=headers,
            timeout=5,
        )
        resp.raise_for_status()
        logging.info(
            "Sent ntfy notification for '%s' to topic '%s'", subject, config.NTFY_TOPIC
        )
    except Exception as e:
        logging.error("Failed to send ntfy notification: %s", e)
