"""
OAuth 2.0 authentication handler for PhishFish
"""

import base64
import http.server
import json
import logging
import socketserver
import threading
import time
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse

from authlib.integrations.requests_client import OAuth2Session


class OAuthError(Exception):
    """Custom exception for OAuth-related errors."""


class OAuthHandler:
    """Handles OAuth 2.0 authentication flow using authlib."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        auth_uri: str,
        token_uri: str,
        scopes: list,
        callback_port: int = 8080,
    ):
        """Initialize OAuth handler."""
        self.auth_uri = auth_uri
        self.token_uri = token_uri

        self.token_file = Path(".data") / "oauth_tokens.json"
        self.token_file.parent.mkdir(exist_ok=True)

        self.session = OAuth2Session(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=f"http://localhost:{callback_port}/callback",
            scope=scopes,
            update_token=self._save_token,
        )

        self._load_tokens()

    def _save_token(self, token, *args, **kwargs):
        """Callback to save token when updated by authlib."""
        _ = args, kwargs
        try:
            with open(self.token_file, "w", encoding="utf-8") as f:
                json.dump(token, f, indent=2)
            self.token_file.chmod(0o600)
            logging.info("Tokens saved automatically")
        except OSError as e:
            logging.error("Failed to save tokens: %s", e)

    def _load_tokens(self):
        """Load existing tokens into session."""
        try:
            if self.token_file.exists():
                with open(self.token_file, "r", encoding="utf-8") as f:
                    token = json.load(f)
                self.session.token = token
                logging.info("Tokens loaded")
        except (OSError, json.JSONDecodeError) as e:
            logging.debug("Could not load existing tokens: %s", e)

    def get_valid_access_token(self) -> Optional[str]:
        """Get a valid access token, refreshing automatically if needed."""
        if not self.session.token:
            logging.info("No tokens found, authentication required")
            return None

        current_time = time.time()
        expires_at = self.session.token.get("expires_at", 0)

        if (
            expires_at and current_time >= expires_at - 60
        ):
            try:
                logging.info("Token expired, refreshing...")
                new_token = self.session.refresh_token(self.token_uri)
                self._save_token(new_token)
                return new_token["access_token"]
            except (OSError, ValueError) as e:
                logging.error("Failed to refresh token: %s", e)
                return None

        try:
            return self.session.token["access_token"]
        except (KeyError, TypeError) as e:
            logging.error("Failed to get access token: %s", e)
            return None

    def get_oauth_string(self, username: str) -> str:
        """Generate OAuth2 SASL string for IMAP authentication."""
        access_token = self.get_valid_access_token()
        if not access_token:
            raise OAuthError("No valid access token available")

        auth_string = f"user={username}\x01auth=Bearer {access_token}\x01\x01"
        return base64.b64encode(auth_string.encode()).decode()

    def authenticate_interactive(self) -> bool:
        """Perform interactive OAuth authentication."""
        try:
            if self.get_valid_access_token():
                logging.info("Already authenticated with valid tokens")
                return True

            authorization_url, _ = self.session.create_authorization_url(
                self.auth_uri, access_type="offline"
            )

            logging.info("Starting interactive OAuth authentication")
            logging.info("Please visit the following URL in your browser:")
            logging.info("%s", authorization_url)

            authorization_code = self._start_callback_server()
            if not authorization_code:
                return False

            token = self.session.fetch_token(
                self.token_uri,
                authorization_response=f"{self.session.redirect_uri}?code={authorization_code}",
            )

            self._save_token(token)

            logging.info("OAuth authentication successful")
            return True

        except (OSError, ValueError) as e:
            logging.error("OAuth authentication failed: %s", e)
            return False

    def _start_callback_server(self) -> Optional[str]:
        """Start local server to handle OAuth callback."""
        authorization_code = None
        server_error = None

        class CallbackHandler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                nonlocal authorization_code, server_error
                parsed_url = urlparse(self.path)
                query_params = parse_qs(parsed_url.query)

                if "code" in query_params:
                    authorization_code = query_params["code"][0]
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"""
                    <html><body>
                    <h2>Authorization successful!</h2>
                    <p>You can close this window and return to PhishFish.</p>
                    </body></html>
                    """)
                elif "error" in query_params:
                    server_error = query_params["error"][0]
                    self.send_response(400)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(
                        f"""
                    <html><body>
                    <h2>Authorization failed!</h2>
                    <p>Error: {server_error}</p>
                    </body></html>
                    """.encode()
                    )

            def log_message(self, format, *args):  # pylint: disable=redefined-builtin
                """Suppress server logs."""

        port = int(self.session.redirect_uri.split(":")[2].split("/")[0])

        try:
            server = socketserver.TCPServer(("", port), CallbackHandler)
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()

            timeout = 300  # 5 minutes
            start_time = time.time()

            while authorization_code is None and server_error is None:
                if time.time() - start_time > timeout:
                    logging.error("Authorization timeout - no callback received")
                    break
                time.sleep(1)

            server.shutdown()
            server.server_close()

            if server_error:
                logging.error("Authorization failed: %s", server_error)
                return None

            return authorization_code

        except (OSError, ValueError) as e:
            logging.error("Failed to start callback server: %s", e)
            return None

    def revoke_tokens(self) -> None:
        """Revoke tokens and delete token file."""
        try:
            if self.token_file.exists():
                self.token_file.unlink()
                logging.info("Token file deleted")
        except OSError as e:
            logging.error("Error revoking tokens: %s", e)


def create_oauth_handler(
    client_id: str,
    client_secret: str,
    auth_uri: str,
    token_uri: str,
    scopes: list,
    callback_port: int = 8080,
) -> OAuthHandler:
    """Create OAuth handler using authlib."""
    return OAuthHandler(
        client_id, client_secret, auth_uri, token_uri, scopes, callback_port
    )
