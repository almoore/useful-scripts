#!/usr/bin/env python3
"""
facebook_get_albums_list.py — Fetch Facebook photo albums and all photos via Graph API.

Retrieves all albums (with backdated_time, created_time, and nested photo sources)
and all photos uploaded by the authenticated user, then writes them to JSON files:
  facebook_albums_data.json      — list of albums with nested photo metadata
  facebook_albums_photos.json    — flat list of photos extracted from albums
  facebook_all_photos.json       — all photos from /me/photos endpoint

Usage:
  export FACEBOOK_ACCESS_TOKEN=<token>
  python3 facebook_get_albums_list.py [--limit N] [--output DIR]

Options:
  --limit N     Number of items per API page (default: 500)
  --output DIR  Directory to write output JSON files (default: current dir)

Requirements: requests, pandas (pip install requests pandas)
"""

import requests
import pandas as pd
import json
import os
import argparse
from datetime import datetime
from urllib.parse import urlparse, parse_qs
# Replace with your own access token
ACCESS_TOKEN = os.environ.get('FACEBOOK_ACCESS_TOKEN')
BASE_URL = 'https://graph.facebook.com/v11.0/me/posts'


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", action='store', default=500, help='Number of post to query at a time')
    parser.add_argument("--output", action='store', help='Output directory')
    return parser.parse_args()


def get_paginated_list(url='https://graph.facebook.com/v22.0/me/',
                       access_token=None,
                       limit=500,
                       fields=["albums.fields(photos.fields(source,created_time))"],
                       params={},
                       key="albums"):
    """Fetch paginated posts from the Facebook Graph API."""
    items = []
    params = {**{
        'access_token': access_token,
        'limit': limit,
    }, **params}
    if fields:
        params['fields'] = ','.join(fields)
    while url:
        parsed_url = urlparse(url)
        query_parameters = parse_qs(parsed_url.query)
        params = {**params, **query_parameters}
        response = requests.get(url, params=params)
        if response.status_code == 200:
            resp = response.json()
            data = []
            # Get the 'next' page URL from the pagination info
            if key in resp.keys():
                data = resp.get(key, {}).get('data', [])
                url = resp.get(key, {}).get('paging', {}).get('next')
            elif "data" in resp.keys():
                data = resp.get("data", [])
                url = resp.get('paging', {}).get('next')
            items.extend(data)
            # print(url)
            print(f"Fetched {len(items)} {key} so far...")
        else:
            print(f"Error reaching API: {response.status_code}")
            break
    return items


def export_to_json(data, json_file='facebook_albums_data.json'):
    if not data:
        print("No data to export.")
        return
    with open(json_file, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Data exported to {json_file}")



def main():
    args = parse_args()
    # print(args)
    params = {}
    prefix = "facebook_albums_data"
    if args.output:
        if not os.path.exists(args.output):
            os.makedirs(args.output)
        os.chdir(args.output)
    try:
        albums = get_paginated_list(access_token=ACCESS_TOKEN, limit=args.limit, params=params, fields=["created_time","backdated_time","photos.fields(source,created_time,link)"], url='https://graph.facebook.com/v22.0/me/albums')
        export_to_json(albums, json_file=f"{prefix}.json")
        photos = []
        for a in albums:
            data = a.get("photos", {}).get("data", [])
            print(f"Album has {len(data)} photos")
            photos.extend(data)
        export_to_json(photos, json_file=f"facebook_albums_photos.json")

        photos = get_paginated_list(access_token=ACCESS_TOKEN, limit=args.limit, params=params, fields=["source","created_time", "name", "link"], key="photos", url='https://graph.facebook.com/v22.0/me/photos')
        print(f"Found {len(photos)} photos")
        export_to_json(photos, json_file=f"facebook_all_photos.json")
    except Exception as e:
        print(f"An error occurred: {e}")
        raise Exception

if __name__ == "__main__":
    main()
