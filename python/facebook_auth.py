#!/usr/bin/env python3
"""
Facebook OAuth login for StoryBound.

Usage:
    python facebook_auth.py --app-id YOUR_APP_ID

    # Or set via environment variables
    FACEBOOK_APP_ID=YOUR_APP_ID FACEBOOK_APP_SECRET=YOUR_SECRET python facebook_auth.py
"""
import argparse
import os
import sys

from posts_to_pdf.oauth import login, get_stored_token, clear_token


def parse_args():
    parser = argparse.ArgumentParser(
        description="Authenticate with Facebook for StoryBound.",
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
