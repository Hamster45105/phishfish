"""
OAuth 2.0 authentication handler for PhishFish application.
"""

import base64
import json
import logging
import time
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Dict, Optional

import requests


class OAuthError(Exception):
    """Custom exception for OAuth-related errors."""


class OAuthHandler:
    """Handles OAuth 2.0 authentication flow for email provider."""

    def __init__(self, client_id: str, client_secret: str, auth_uri: str, token_uri: str, scopes: list, callback_port: int = 8080):
        """
        Initialize OAuth handler.
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth_uri = auth_uri
        self.token_uri = token_uri
        self.scopes = scopes
        self.callback_port = callback_port
        self.redirect_uri = f"http://localhost:{callback_port}/callback"

        # Use .data directory for persistent storage
        data_dir = Path(".data")
        self.token_file = data_dir / "oauth_tokens.json"

        # Ensure token directory exists
        self.token_file.parent.mkdir(exist_ok=True)

    def get_authorization_url(self) -> str:
        """
        Generate the OAuth authorization URL.
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "response_type": "code",
            "access_type": "offline",  # For refresh tokens
            "prompt": "consent",  # Force consent to ensure refresh token
        }

        query_string = urllib.parse.urlencode(params)
        return f"{self.auth_uri}?{query_string}"

    def exchange_code_for_tokens(self, authorization_code: str) -> Dict:
        """
        Exchange authorization code for access and refresh tokens.
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": authorization_code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        response = requests.post(
            self.token_uri,
            data=data,
            headers=headers,
            timeout=30
        )

        if response.status_code != 200:
            raise OAuthError(f"Token exchange failed: {response.status_code} {response.text}")

        tokens = response.json()

        # Add expiration timestamp
        if "expires_in" in tokens:
            tokens["expires_at"] = time.time() + int(tokens["expires_in"])

        # Save tokens
        self.save_tokens(tokens)

        return tokens

    def refresh_access_token(self, refresh_token: str) -> Dict:
        """
        Refresh the access token using the refresh token.
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        response = requests.post(
            self.token_uri,
            data=data,
            headers=headers,
            timeout=30
        )

        if response.status_code != 200:
            raise OAuthError(f"Token refresh failed: {response.status_code} {response.text}")

        tokens = response.json()

        # Add expiration timestamp
        if "expires_in" in tokens:
            tokens["expires_at"] = time.time() + int(tokens["expires_in"])

        # Preserve the refresh token if not returned
        if "refresh_token" not in tokens:
            tokens["refresh_token"] = refresh_token

        # Save updated tokens
        self.save_tokens(tokens)

        return tokens

    def save_tokens(self, tokens: Dict) -> None:
        """
        Save tokens to file.
        """
        try:
            with open(self.token_file, "w", encoding="utf-8") as f:
                json.dump(tokens, f, indent=2)

            # Set restrictive permissions
            self.token_file.chmod(0o600)
            logging.info("Tokens saved to %s", self.token_file)
        except Exception as e:
            logging.error("Failed to save tokens: %s", e)
            raise

    def load_tokens(self) -> Optional[Dict]:
        """
        Load tokens from file.
        """
        try:
            if not self.token_file.exists():
                return None

            with open(self.token_file, "r", encoding="utf-8") as f:
                tokens = json.load(f)

            logging.info("Tokens loaded from %s", self.token_file)
            return tokens
        except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
            logging.error("Failed to load tokens: %s", e)
            return None

    def get_valid_access_token(self) -> Optional[str]:
        """
        Get a valid access token, refreshing if necessary.
        """
        tokens = self.load_tokens()
        if not tokens:
            logging.info("No tokens found, authentication required")
            return None

        # Check if token is still valid
        if "expires_at" in tokens and tokens["expires_at"] > time.time() + 60:
            logging.debug("Access token is still valid")
            return tokens["access_token"]

        # Try to refresh the token
        if "refresh_token" in tokens:
            try:
                logging.info("Access token expired, refreshing...")
                new_tokens = self.refresh_access_token(tokens["refresh_token"])
                return new_tokens["access_token"]
            except OAuthError as e:
                logging.error("Failed to refresh token: %s", e)
                return None

        logging.info("No refresh token available, re-authentication required")
        return None

    def get_oauth_string(self, username: str) -> str:
        """
        Generate OAuth2 SASL string for IMAP authentication.
        """
        access_token = self.get_valid_access_token()
        if not access_token:
            raise OAuthError("No valid access token available")

        # Create OAuth2 SASL string
        auth_string = f"user={username}\x01auth=Bearer {access_token}\x01\x01"

        # Base64 encode
        return base64.b64encode(auth_string.encode()).decode()

    def start_local_server(self, port: Optional[int] = None) -> str:
        """
        Start a local server to handle OAuth callback.
        """
        if port is None:
            port = self.callback_port
        import http.server
        import socketserver
        import threading
        from urllib.parse import parse_qs, urlparse

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
                    self.wfile.write(f"""
                    <html><body>
                    <h2>Authorization failed!</h2>
                    <p>Error: {server_error}</p>
                    </body></html>
                    """.encode())
                else:
                    self.send_response(400)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"""
                    <html><body>
                    <h2>Invalid callback</h2>
                    <p>No authorization code received.</p>
                    </body></html>
                    """)

            def log_message(self, format, *args):
                # Suppress server logs to reduce noise
                pass

        # Start server in a separate thread
        server = socketserver.TCPServer(("", port), CallbackHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        try:
            # Wait for callback with timeout
            timeout = 300  # 5 minutes
            start_time = time.time()

            while authorization_code is None and server_error is None:
                if time.time() - start_time > timeout:
                    raise OAuthError("Authorization timeout - no callback received")
                time.sleep(1)

            if server_error:
                raise OAuthError(f"Authorization failed: {server_error}")

            if authorization_code is None:
                raise OAuthError("No authorization code received")

            return authorization_code
        finally:
            server.shutdown()
            server.server_close()

    def authenticate_interactive(self) -> bool:
        """
        Perform interactive OAuth authentication.
        """
        try:
            # Check if we already have valid tokens
            if self.get_valid_access_token():
                logging.info("Already authenticated with valid tokens")
                return True

            # Generate authorization URL
            auth_url = self.get_authorization_url()

            logging.info("Starting interactive OAuth authentication")
            logging.info("Opening browser for authorization at: %s", auth_url)

            # Open browser first, then start server
            try:
                webbrowser.open(auth_url)
                logging.info("Browser opened successfully")
            except (OSError, webbrowser.Error) as e:
                logging.warning("Could not open browser automatically: %s", e)
                logging.info("Please manually visit: %s", auth_url)

            # Start local server and wait for callback
            try:
                authorization_code = self.start_local_server()
            except (OSError, ConnectionError) as e:
                logging.error("Failed to start local callback server: %s", e)
                return False

            # Exchange code for tokens
            self.exchange_code_for_tokens(authorization_code)
            logging.info("OAuth authentication successful")

            return True

        except (OAuthError, OSError, ConnectionError) as e:
            logging.error("OAuth authentication failed: %s", e)
            return False

    def revoke_tokens(self) -> None:
        """Revoke tokens and delete token file."""
        try:
            # Delete token file
            if self.token_file.exists():
                self.token_file.unlink()
                logging.info("Token file deleted: %s", self.token_file)

        except (OSError,) as e:
            logging.error("Error revoking tokens: %s", e)


def create_oauth_handler(client_id: str, client_secret: str, auth_uri: str, token_uri: str, scopes: list, callback_port: int = 8080) -> OAuthHandler:
    """
    Function to create OAuth handler.
    """
    return OAuthHandler(client_id, client_secret, auth_uri, token_uri, scopes, callback_port)
