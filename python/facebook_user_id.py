import requests
import os

# Replace 'PAGE_USERNAME' with the public page username
PAGE_USERNAME = 'kerstin.moore'
ACCESS_TOKEN = os.environ.get('FACEBOOK_ACCESS_TOKEN')
BASE_URL = f'https://graph.facebook.com/v22.0/{PAGE_USERNAME}'

def get_page_id():
    response = requests.get(BASE_URL, params={'access_token': ACCESS_TOKEN, 'fields': 'id,name'})
    if response.status_code == 200:
        page_data = response.json()
        return page_data.get('id'), page_data.get('name')
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

if __name__ == "__main__":
    page_id, page_name = get_page_id()
    if page_id:
        print(f"Page Name: {page_name}, Page ID: {page_id}")
