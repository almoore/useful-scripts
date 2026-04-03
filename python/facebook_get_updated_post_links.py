#!/usr/bin/env python3
"""
facebook_get_updated_post_links.py — Re-fetch current Graph API URLs for photos in a post export.

Takes a Facebook JSON export file (posts with attachments) and looks up the live
photo source URL for each attachment by extracting the photo ID from the local URI
and querying the Graph API. Useful when local export URIs have expired or changed.

Output: facebook_updated_photos_list.json (list of photo objects with source, link, etc.)

Usage:
  export FACEBOOK_ACCESS_TOKEN=<token>
  python3 facebook_get_updated_post_links.py --input posts.json [--output DIR] [--style post]

Options:
  --input FILE   JSON export file containing posts with attachments (required)
  --output DIR   Directory to write output JSON (default: current dir)
  --style STR    Input format hint: post, photos, album, or list

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
ACCESS_TOKEN = os.environ.get("FACEBOOK_ACCESS_TOKEN")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", action="store", help="Input file with problem posts (as json)"
    )
    parser.add_argument("--output", action="store", help="Output directory")
    parser.add_argument(
        "--style",
        action="store",
        help="Style of json list, (post, photos, album, list)",
    )

    return parser.parse_args()


def get_item(
    item_id,
    url="https://graph.facebook.com/v11.0",
    access_token=None,
    fields=["source", "created_time", "link"],
    params={},
):
    item_url = "/".join([url, item_id])
    params = {
        **{
            "access_token": access_token,
        },
        **params,
    }
    if fields:
        params["fields"] = ",".join(fields)
    parsed_url = urlparse(item_url)
    query_parameters = parse_qs(parsed_url.query)
    params = {**params, **query_parameters}
    response = requests.get(item_url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error reaching API: {response.status_code}")


def export_to_json(data, json_file="facebook_albums_data.json"):
    if not data:
        print("No data to export.")
        return
    with open(json_file, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Data exported to {json_file}")


def main():
    args = parse_args()
    # print(args)
    try:
        photos = []
        with open(args.input) as f:
            posts = json.load(f)
        for post in posts:
            for attachment in post.get("attachments"):
                for data in attachment.get('data', []):
                    media_uri = data.get("media", {}).get("uri")
                    if media_uri is None:
                        continue
                    link_filename = os.path.basename(media_uri)
                    item_id = link_filename.removesuffix(
                        os.path.splitext(link_filename)[-1]
                    ).split("_n_")[-1]
                    photo = get_item(
                        item_id,
                        access_token=ACCESS_TOKEN,
                        fields=["source", "created_time", "name", "link"],
                    )
                    if photo:
                        photos.append(photo)
        if args.output:
            if not os.path.exists(args.output):
                os.makedirs(args.output)
            os.chdir(args.output)
        export_to_json(photos, json_file=f"facebook_updated_photos_list.json")
    except Exception as e:
        print(f"An error occurred: {e}")
        raise Exception


if __name__ == "__main__":
    main()
