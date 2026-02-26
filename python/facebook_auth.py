#!/usr/bin/env python3
"""
Facebook OAuth dialog helper.

Usage:
    python facebook_auth.py --client-id YOUR_APP_ID

    # Or set via environment variable
    FACEBOOK_CLIENT_ID=YOUR_APP_ID python facebook_auth.py
"""
import argparse
import os
import sys

import requests


def parse_args():
    parser = argparse.ArgumentParser(
        description="Initiate Facebook OAuth dialog.",
    )
    parser.add_argument(
        "--client-id",
        default=os.environ.get("FACEBOOK_CLIENT_ID"),
        help="Facebook app client ID (or set FACEBOOK_CLIENT_ID env var).",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.client_id:
        print("Error: --client-id or FACEBOOK_CLIENT_ID env var required.",
              file=sys.stderr)
        sys.exit(1)

    url = "https://www.facebook.com/dialog/oauth"
    params = {"client_id": args.client_id}
    response = requests.get(url, params=params)
    print(response.text)


if __name__ == "__main__":
    main()
