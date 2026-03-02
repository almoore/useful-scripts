#!/usr/bin/env python3
"""Check Facebook Graph API rate limit status for the current access token."""

import json
import os
import sys

import requests

token = os.environ.get("FACEBOOK_ACCESS_TOKEN")
if not token:
    print("Error: FACEBOOK_ACCESS_TOKEN not set", file=sys.stderr)
    sys.exit(1)

resp = requests.get(
    "https://graph.facebook.com/v22.0/me/posts",
    params={"access_token": token, "limit": 1},
    timeout=10,
)
usage = json.loads(resp.headers.get("x-app-usage", "{}"))

print(f"Status: {resp.status_code}")
print(f"call_count: {usage.get('call_count')}%")
print(f"total_cputime: {usage.get('total_cputime')}%")
print(f"total_time: {usage.get('total_time')}%")

if resp.status_code == 403:
    print("\nRate limited — wait for usage to drop below 100%.")
