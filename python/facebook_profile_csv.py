#!/usr/bin/env python3

import requests
import pandas as pd
import json
import os

# Replace with your own access token
ACCESS_TOKEN = os.environ.get('FACEBOOK_ACCESS_TOKEN')
BASE_URL = 'https://graph.facebook.com/v11.0/me'

def fetch_facebook_profile_data(access_token, fields=None):
    """Fetches profile data from Facebook."""
    params = {
        'access_token': access_token,
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
    # Define the fields you want to retrieve
    fields = ['id', 'name', 'posts']  # modify according to permissions granted

    try:
        profile_data = fetch_facebook_profile_data(ACCESS_TOKEN, fields)
        # print(json.dumps(profile_data, indent=2))
        posts = profile_data.get("posts").get("data")
        export_to_json(posts)
        export_to_csv(posts)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
