"""
Configuration module for PhishFish application.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file if it exists (for local development)
dotenv_path = Path(__file__).resolve().parent.parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path, override=True)

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
if log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    raise ValueError(
        f"Invalid LOG_LEVEL: {log_level}. Must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL."
    )
logging.basicConfig(
    level=getattr(logging, log_level), format="%(asctime)s [%(levelname)s] %(message)s"
)


class Config:
    """Configuration class containing all application settings."""

    # IMAP settings
    IMAP_HOST = os.environ["IMAP_HOST"]
    IMAP_USER = os.environ["IMAP_USER"]
    IMAP_PASS = os.environ.get("IMAP_PASS", "")
    IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
    IMAP_ENCRYPTION_METHOD = os.getenv("IMAP_ENCRYPTION_METHOD", "SSL").upper()
    MAILBOX = os.getenv("IMAP_MAILBOX", "INBOX")

    # IMAP move settings
    MOVE_TO_FOLDER = os.getenv("MOVE_TO_FOLDER", "")
    IMAP_MOVE = bool(MOVE_TO_FOLDER.strip())

    # ntfy settings
    NTFY_TOPIC = os.getenv("NTFY_TOPIC", "")
    NTFY_ENABLED = bool(NTFY_TOPIC.strip())
    NTFY_URL = os.getenv("NTFY_URL", "https://ntfy.sh")
    NTFY_TITLE = os.getenv("NTFY_TITLE", "PhishFish Email Report")
    NOTIFY_ON = [
        c.strip().lower() for c in os.getenv("NOTIFY_ON", "phishing").split(",")
    ]

    # Azure AI settings
    GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
    AZURE_MODEL = os.getenv("AZURE_MODEL", "openai/gpt-4.1")
    AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT", "https://models.github.ai/inference")

    # OAuth settings
    USE_OAUTH = os.getenv("USE_OAUTH", "false").lower() == "true"
    OAUTH_CLIENT_ID = os.getenv("OAUTH_CLIENT_ID", "")
    OAUTH_CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET", "")
    OAUTH_AUTH_URL = os.getenv("OAUTH_AUTH_URL", "")
    OAUTH_TOKEN_URL = os.getenv("OAUTH_TOKEN_URL", "")
    OAUTH_SCOPE = os.getenv("OAUTH_SCOPE", "")
    OAUTH_CALLBACK_PORT = int(os.getenv("OAUTH_CALLBACK_PORT", "8080"))

    @classmethod
    def validate(cls):
        """Validate configuration and log warnings for optional settings."""
        if not cls.NTFY_ENABLED:
            logging.warning("NTFY_TOPIC is not set, notifications will not be sent.")

        if not cls.IMAP_MOVE:
            logging.warning(
                "MOVE_TO_FOLDER is not set, emails will not be moved after processing."
            )

        # Validate OAuth settings
        if cls.USE_OAUTH:
            if not cls.OAUTH_CLIENT_ID or not cls.OAUTH_CLIENT_SECRET:
                raise ValueError("OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET must be set when USE_OAUTH is true")
            if not cls.OAUTH_AUTH_URL or not cls.OAUTH_TOKEN_URL:
                raise ValueError("OAUTH_AUTH_URL and OAUTH_TOKEN_URL must be set when USE_OAUTH is true")
            if not cls.OAUTH_SCOPE:
                raise ValueError("OAUTH_SCOPE must be set when USE_OAUTH is true")
        else:
            if not cls.IMAP_PASS:
                raise ValueError("IMAP_PASS must be set when USE_OAUTH is false")

    @property
    def ntfy_full_url(self):
        """Get the full ntfy URL including topic."""
        return f"{self.NTFY_URL}/{self.NTFY_TOPIC}"


# Global config instance
config = Config()
config.validate()
