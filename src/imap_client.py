"""
IMAP client operations for PhishFish application.
"""

import logging
import sys
import time
import traceback

from imapclient import IMAPClient
from imapclient.exceptions import LoginError

from ai_classifier import classifier
from config import config
from email_parser import format_email, parse_email_bytes
from notifications import notify_user


class EmailProcessor:
    """Handles IMAP operations and email processing."""

    def __init__(self):
        """Initialize the email processor."""
        self.imap_client = None

    def connect(self):
        """Establish IMAP connection."""
        logging.info(
            "Connecting to IMAP %s:%d using %s",
            config.IMAP_HOST,
            config.IMAP_PORT,
            config.IMAP_ENCRYPTION_METHOD,
        )

        if config.IMAP_ENCRYPTION_METHOD in ("SSL", "TLS"):
            self.imap_client = IMAPClient(
                config.IMAP_HOST, port=config.IMAP_PORT, ssl=True
            )
        elif config.IMAP_ENCRYPTION_METHOD == "STARTTLS":
            self.imap_client = IMAPClient(
                config.IMAP_HOST, port=config.IMAP_PORT, ssl=False
            )
            self.imap_client.starttls()
        else:
            self.imap_client = IMAPClient(
                config.IMAP_HOST, port=config.IMAP_PORT, ssl=False
            )

        self.imap_client.login(config.IMAP_USER, config.IMAP_PASS)
        self.imap_client.select_folder(config.MAILBOX)

    def print_available_folders(self):
        """Print all available IMAP folders for the current account."""
        folders = self.imap_client.list_folders()
        logging.info("Available IMAP folders:")
        for _, _, folder_name in folders:
            logging.info("  - %s", folder_name)
        return folders

    def move_email(self, uid, result):
        """Move email to a specified folder."""
        if not config.IMAP_MOVE:
            return

        # result is a dict from classify_email
        cls = result.get("classification", "").lower()
        # Skip moving if not phishing
        if cls != "phishing":
            return

        try:
            self.imap_client.move(uid, config.MOVE_TO_FOLDER)
            logging.info("Moved UID %s to folder '%s'", uid, config.MOVE_TO_FOLDER)
        except Exception as e:
            logging.error(
                "Failed to move UID %s to folder '%s': %s",
                uid,
                config.MOVE_TO_FOLDER,
                e,
            )

    def process_single_email(self, uid):
        """Process a single email UID - fetch, classify, and notify."""
        try:
            # Fetch email data with error handling for missing UIDs
            fetch_result = self.imap_client.fetch(uid, ["BODY.PEEK[]"])

            data = fetch_result[uid]
            raw = data.get(b"BODY[]")
            if not isinstance(raw, (bytes, bytearray)):
                logging.warning("Skipping UID %s: invalid format", uid)
                # Only try to flag if the UID still exists
                self.imap_client.add_flags(uid, "PhishFish_Processed")
                return

            metadata, body, urls = parse_email_bytes(raw)
            preview = format_email(metadata, body, urls)
            logging.info("Email UID %s sent to AI for classification", uid)

            result = classifier.classify_email(preview)
            logging.info(
                "UID %s classified as '%s'", uid, result.get("classification", "")
            )

            notify_user(metadata["from"], metadata["subject"], result)

            # Mark as processed (but keep unread if legitimate)
            try:
                self.imap_client.add_flags(uid, "PhishFish_Processed")
                # Verify the flag was set
                flags_data = self.imap_client.fetch(uid, ["FLAGS"])[uid]
                current_flags = flags_data.get(b"FLAGS", [])
                logging.info("UID %s processed and flagged: %s", uid, current_flags)
            except Exception as e:
                logging.warning(
                    "Could not flag UID %s as processed: %s - email may no longer exist",
                    uid,
                    e,
                )

            self.move_email(uid, result)

        except Exception as e:
            logging.error("Error processing email UID %s: %s", uid, str(e))
            logging.error("Exception type: %s", type(e).__name__)
            logging.error("Traceback: %s", traceback.format_exc())
            # Still mark as processed to avoid reprocessing failures
            try:
                self.imap_client.add_flags(uid, "PhishFish_Processed")
            except Exception as flag_error:
                logging.warning(
                    "Could not flag UID %s as processed after error: %s - email may no longer exist",
                    uid,
                    flag_error,
                )

    def process_unseen(self):
        """Find all UNSEEN and unprocessed messages and process them immediately."""
        uids = self.imap_client.search(
            ["UNSEEN", "NOT", "KEYWORD", "PhishFish_Processed"]
        )
        logging.info(
            "Found %d unseen, unprocessed messages in '%s'", len(uids), config.MAILBOX
        )
        for uid in uids:
            self.process_single_email(uid)

    def monitor_mailbox_idle(self):
        """Connect once, then enter IMAP IDLE to process new mail immediately."""
        logging.info("Starting IMAP IDLE monitor")

        try:
            self.connect()
            # Print all available folders after login
            self.print_available_folders()
            logging.info("Authenticated – entering IDLE")
            self.process_unseen()

        except LoginError as e:
            logging.error("IMAP login failed: %s", e)
            sys.exit(1)
        except Exception as e:
            logging.error("Failed to initialize: %s", e)
            sys.exit(1)

        # Main IDLE loop with exponential back-off and connection management
        backoff = 5
        max_backoff = 300
        idle_timeout = 120
        last_noop = time.time()
        noop_interval = 600

        try:
            while True:
                try:
                    # Send periodic NOOP to keep connection alive
                    if time.time() - last_noop > noop_interval:
                        try:
                            self.imap_client.noop()
                            last_noop = time.time()
                            logging.debug("Sent NOOP keepalive")
                        except Exception as noop_error:
                            logging.warning("NOOP keepalive failed: %s", noop_error)
                            raise noop_error  # Trigger reconnection

                    logging.info("Entering IMAP IDLE")
                    self.imap_client.idle()
                    responses = self.imap_client.idle_check(timeout=idle_timeout)
                    self.imap_client.idle_done()
                    logging.debug("IDLE returned responses: %s", responses)

                    # Reset backoff on successful IDLE
                    backoff = 5

                    for resp in responses:
                        if (
                            isinstance(resp, tuple)
                            and len(resp) > 1
                            and resp[1] == b"EXISTS"
                        ):
                            logging.info("New email detected; processing immediately")
                            self.process_unseen()
                            break

                except Exception as e:
                    logging.error(
                        "Error in IDLE loop: %s; reconnecting in %ds", e, backoff
                    )

                    # Close old connection
                    try:
                        self.imap_client.logout()
                    except:
                        pass

                    time.sleep(backoff)
                    backoff = min(backoff * 2, max_backoff)

                    # Reconnect
                    try:
                        self.connect()
                        logging.info("Reconnected to IMAP server")
                    except Exception as reconnect_error:
                        logging.error("Failed to reconnect: %s", reconnect_error)

        except KeyboardInterrupt:
            logging.info("Received interrupt signal, shutting down...")
        finally:
            if self.imap_client:
                try:
                    self.imap_client.logout()
                except:
                    pass
