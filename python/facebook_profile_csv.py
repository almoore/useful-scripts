#!/usr/bin/env python3

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
    parser.add_argument('--since', action='store', help='Date to start')
    parser.add_argument("--until", action='store', help='Date to end')
    parser.add_argument("--limit", action='store', default=500, help='Number of post to query at a time')
    parser.add_argument('--no-paginate', action='store_false', dest="paginate",
                        default=True, help='Turn of pagination of image tags')
    return parser.parse_args()


def get_paginated_posts(url='https://graph.facebook.com/v22.0/me/posts',
                        access_token=None,
                        limit=500,
                        fields=None,
                        params={}):
    """Fetch paginated posts from the Facebook Graph API."""
    posts = []
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
            data = response.json()
            posts.extend(data.get('data', []))
            # Get the 'next' page URL from the pagination info
            url = data.get('paging', {}).get('next')
            # print(url)
            print(f"Fetched {len(posts)} posts so far...")
        else:
            print(f"Error reaching API: {response.status_code}")
            break
    return posts


def fetch_facebook_profile_data(access_token, fields=None, limit=50):
    """Fetches profile data from Facebook."""
    params = {
        'access_token': access_token,
        'limit': limit,
    }
    if fields:
        params['fields'] = ','.join(fields)

    response = requests.get(BASE_URL, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Error fetching data: {response.status_code} {response.text}")


def export_to_json(data, json_file='facebook_profile_data.json'):
    if not data:
        print("No data to export.")
        return
    with open(json_file, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Data exported to {json_file}")


def export_to_csv(data, csv_file='facebook_profile_data.csv'):
    """Exports the fetched data to a CSV file."""
    if not data:
        print("No data to export.")
        return

    if isinstance(data, dict):
        data = [data]

    df = pd.DataFrame(data)
    df.to_csv(csv_file, index=False)
    print(f"Data exported to {csv_file}")


def main():
    args = parse_args()
    print(args)
    # Define the fields you want to retrieve
    # modify according to permissions granted
    fields = ["attachments", "type", "updated_time", "full_picture",
              "created_time", "backdated_time", "message", "source"]

    try:
        prefix = "facebook_profile_data"
        if args.paginate:
            params = {}
            if args.since:
                date_format = "%Y-%m-%d"
                date_string = args.since
                datetime_object = datetime.strptime(date_string, date_format)
                since = datetime_object.timestamp()
                params['since'] = since
            if args.until:
                date_format = "%Y-%m-%d"
                date_string = args.until
                datetime_object = datetime.strptime(date_string, date_format)
                until = datetime_object.timestamp()
                params['until'] = until
                prefix = f"{prefix}_{date_string}"
            posts = get_paginated_posts(access_token=ACCESS_TOKEN, fields=fields, limit=args.limit, params=params)
        else:
            profile_data = fetch_facebook_profile_data(ACCESS_TOKEN, fields, limit=args.limit)
            # print(json.dumps(profile_data, indent=2))
            posts = profile_data.get("posts").get("data")
        export_to_json(posts, json_file=f"{prefix}.json")
        export_to_csv(posts, csv_file=f"{prefix}.csv")
    except Exception as e:
        print(f"An error occurred: {e}")
        raise Exception

if __name__ == "__main__":
    main()
