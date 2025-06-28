"""
Main entry point for PhishFish application.
Background job to poll emails via IMAP and notify users of phishing.
"""

from imap_client import EmailProcessor

if __name__ == "__main__":
    processor = EmailProcessor()
    processor.monitor_mailbox_idle()
