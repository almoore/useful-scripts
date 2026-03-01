#!/usr/bin/env python3
"""
Facebook OAuth login — standalone helper.

Performs the browser-based Facebook OAuth 2.0 authorization code flow,
exchanges the code for an access token, and stores it locally via
the system keyring (if available) or ~/.facebook_oauth.json.

Usage:
    python facebook_auth.py --app-id YOUR_APP_ID

    # Or set via environment variables
    FACEBOOK_APP_ID=YOUR_APP_ID FACEBOOK_APP_SECRET=YOUR_SECRET python facebook_auth.py
"""
import argparse
import http.server
import json
import os
import secrets
import sys
import urllib.parse
import webbrowser

try:
    import keyring
    _HAS_KEYRING = True
except ImportError:
    _HAS_KEYRING = False

GRAPH_API_VERSION = "v22.0"
OAUTH_DIALOG_URL = f"https://www.facebook.com/{GRAPH_API_VERSION}/dialog/oauth"
TOKEN_EXCHANGE_URL = (
    f"https://graph.facebook.com/{GRAPH_API_VERSION}/oauth/access_token"
)
DEFAULT_SCOPES = ["user_posts", "user_photos"]
CALLBACK_PORT = 8910
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/callback"

_KEYRING_SERVICE = "facebook-oauth"
_CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".facebook_oauth.json")


# ---------------------------------------------------------------------------
# Token storage
# ---------------------------------------------------------------------------

def _load_config():
    try:
        with open(_CONFIG_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_config(conf):
    with open(_CONFIG_PATH, "w") as f:
        json.dump(conf, f, indent=2)


def save_token(token, *, app_id=None):
    if _HAS_KEYRING:
        keyring.set_password(_KEYRING_SERVICE, "access_token", token)
    else:
        conf = _load_config()
        conf["access_token"] = token
        _save_config(conf)
    if app_id:
        conf = _load_config()
        conf["app_id"] = app_id
        _save_config(conf)


def get_stored_token():
    if _HAS_KEYRING:
        token = keyring.get_password(_KEYRING_SERVICE, "access_token")
        if token:
            return token
    conf = _load_config()
    return conf.get("access_token")


def get_stored_app_id():
    conf = _load_config()
    return conf.get("app_id")


def clear_token():
    if _HAS_KEYRING:
        try:
            keyring.delete_password(_KEYRING_SERVICE, "access_token")
        except keyring.errors.PasswordDeleteError:
            pass
    conf = _load_config()
    conf.pop("access_token", None)
    _save_config(conf)


# ---------------------------------------------------------------------------
# OAuth callback server
# ---------------------------------------------------------------------------

class _OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    token = None
    error = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            _OAuthCallbackHandler.token = params["code"][0]
            self._respond("Login successful! You can close this tab.")
        elif "error" in params:
            _OAuthCallbackHandler.error = params.get(
                "error_description", params["error"]
            )
            if isinstance(_OAuthCallbackHandler.error, list):
                _OAuthCallbackHandler.error = _OAuthCallbackHandler.error[0]
            self._respond(f"Login failed: {_OAuthCallbackHandler.error}")
        else:
            self._respond("Unexpected callback — no code or error received.")

    def _respond(self, body):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        html = (
            "<!DOCTYPE html><html><head>"
            "<title>Facebook Auth</title></head><body>"
            f"<h2>{body}</h2></body></html>"
        )
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        pass


# ---------------------------------------------------------------------------
# Login flow
# ---------------------------------------------------------------------------

def login(app_id=None, app_secret=None, scopes=None, timeout=120):
    """Run the Facebook OAuth 2.0 authorization code flow.

    Opens the user's browser, starts a local HTTP server for the redirect,
    exchanges the code for an access token, and stores it.
    """
    import requests

    app_id = app_id or os.environ.get("FACEBOOK_APP_ID") or get_stored_app_id()
    if not app_id:
        raise RuntimeError(
            "Facebook app ID required. Pass --app-id or set FACEBOOK_APP_ID."
        )

    app_secret = app_secret or os.environ.get("FACEBOOK_APP_SECRET")
    if not app_secret:
        raise RuntimeError(
            "Facebook app secret required. Set FACEBOOK_APP_SECRET env var."
        )

    scopes = scopes or DEFAULT_SCOPES
    state = secrets.token_urlsafe(16)

    auth_params = urllib.parse.urlencode({
        "client_id": app_id,
        "redirect_uri": REDIRECT_URI,
        "scope": ",".join(scopes),
        "response_type": "code",
        "state": state,
    })
    auth_url = f"{OAUTH_DIALOG_URL}?{auth_params}"

    _OAuthCallbackHandler.token = None
    _OAuthCallbackHandler.error = None

    server = http.server.HTTPServer(
        ("127.0.0.1", CALLBACK_PORT), _OAuthCallbackHandler
    )
    server.timeout = timeout

    print("Opening browser for Facebook login...")
    print(f"  (If the browser doesn't open, visit: {auth_url})")
    webbrowser.open(auth_url)

    server.handle_request()
    server.server_close()

    if _OAuthCallbackHandler.error:
        raise RuntimeError(
            f"Facebook login failed: {_OAuthCallbackHandler.error}"
        )

    code = _OAuthCallbackHandler.token
    if not code:
        raise RuntimeError("No authorization code received (login timed out?).")

    resp = requests.get(TOKEN_EXCHANGE_URL, params={
        "client_id": app_id,
        "redirect_uri": REDIRECT_URI,
        "client_secret": app_secret,
        "code": code,
    })
    if resp.status_code != 200:
        try:
            err = resp.json().get("error", {}).get("message", resp.text)
        except Exception:
            err = resp.text
        raise RuntimeError(f"Token exchange failed: {err}")

    data = resp.json()
    token = data["access_token"]

    save_token(token, app_id=app_id)
    print("Login successful! Token stored for future use.")
    return token


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Authenticate with Facebook via OAuth 2.0.",
    )
    parser.add_argument(
        "--app-id",
        default=os.environ.get("FACEBOOK_APP_ID"),
        help="Facebook app ID (or set FACEBOOK_APP_ID env var).",
    )
    parser.add_argument(
        "--logout", action="store_true",
        help="Clear stored credentials and exit.",
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Check if a token is stored.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.logout:
        clear_token()
        print("Stored Facebook credentials cleared.")
        return

    if args.status:
        token = get_stored_token()
        if token:
            print(f"Token stored: {token[:12]}...{token[-4:]}")
        else:
            print("No token stored. Run with --app-id to log in.")
        return

    if not args.app_id:
        print("Error: --app-id or FACEBOOK_APP_ID env var required.",
              file=sys.stderr)
        sys.exit(1)

    token = login(app_id=args.app_id)
    print(f"Access token: {token[:12]}...{token[-4:]}")


if __name__ == "__main__":
    main()
