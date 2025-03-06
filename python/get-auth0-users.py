import requests
import argparse
import os
import json
from datetime import datetime, timedelta, timezone


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d", "--domain", default=os.environ.get("AUTH0_DOMAIN","anthemai-dev.us.auth0.com"), help="Your Auth0 Domain ID"
    )
    parser.add_argument(
        "-i", "--client-id", default=os.environ.get("AUTH0_CLIENT_ID", None), help="Skip updating submodule"
    )
    parser.add_argument(
        "-s", "--client-secret", default=os.environ.get("AUTH0_CLIENT_SECRET", None), help="print debugging output"
    )
    parser.add_argument("--days", type=int, default=(365*2), help="Number of days older than to cut off default is 2 years")
    return parser.parse_args()


def get_access_token(domain, client_id, client_secret):
    url = f"https://{domain}/oauth/token"
    headers = {'content-type': 'application/json'}
    payload = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'audience': f'https://{domain}/api/v2/'
    }

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json().get('access_token')


def get_users_with_pagination(domain, access_token, page=0, per_page=50):
    url = f"https://{domain}/api/v2/users"
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {
        'page': page,
        'per_page': per_page,
        'include_totals': 'true',
        'include_fields':  'true'
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def get_auth0_users_before_date(domain, access_token, cutoff_date):
    url = f"https://{domain}/api/v2/users"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    params = {
        'q': f'last_login:[* TO {cutoff_date}]',
        'search_engine': 'v3',
        'per_page': 50,
        'include_totals': 'true',
        'include_fields': 'true'
    }

    users = []
    page = 0
    while True:
        params['page'] = page
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        users.extend(data.get('users', []))

        if not data.get('users') or data.get('start') + data.get('limit') >= data.get('total'):
            break

        page += 1

    return users


def fetch_users(domain, token):
    page = 0
    per_page = 50
    users = []
    while True:
        print(f"Getting page {page}")
        users_data = get_users_with_pagination(domain, token, page, per_page)
        users += users_data.get('users', [])
        total_pages = users_data.get('total') / per_page
        if not users or total_pages <= page + 1:
            break  # Exit if no more users or pages

        page += 1
    return users


def main():
    args = parse_args()

    if args.client_id is None:
        print('Need YOUR CLIENT_ID')
        exit(1)

    if args.client_secret is None:
        print('Need YOUR CLIENT_SECRET')
        exit(1)

    try:
        # Get access token
        token = get_access_token(args.domain, args.client_id, args.client_secret)
        # users = fetch_users(args.domain, token)
        days = args.days
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_date_str = cutoff_date.isoformat()
        users = get_auth0_users_before_date(args.domain, token, cutoff_date_str)

        print(f"Found {len(users)} users")
        with open("users.json", "w") as f:
            json.dump(users, f, indent=2)

    except Exception as e:
        print(f'An error occurred: {str(e)}')

if __name__ == '__main__':
    main()
