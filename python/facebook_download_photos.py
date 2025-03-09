import requests
import os

# Replace with your access token
ACCESS_TOKEN = 'YOUR_ACCESS_TOKEN'
BASE_URL = 'https://graph.facebook.com/v22.0/me/posts'

def download_file(url, dest_folder):
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    filename = os.path.join(dest_folder, url.split('/')[-1])
    
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(filename, 'wb') as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
        print(f"Downloaded: {filename}")
    else:
        print(f"Failed to download file from {url}")

def process_attachments(attachments):
    urls = []
    for attachment in attachments:
        if 'media' in attachment and 'image' in attachment['media']:
            media_url = attachment['media']['image']['src']
            urls.append(media_url)
        if 'subattachments' in attachment:
            subattachments = attachment['subattachments']['data']
            urls.extend(process_attachments(subattachments))
    return urls

def get_posts_with_attachments():
    url = BASE_URL
    all_attachments = []

    while url:
        response = requests.get(url, params={'access_token': ACCESS_TOKEN, 'fields': 'attachments'})
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            return all_attachments
        
        data = response.json()
        for post in data.get('data', []):
            if 'attachments' in post:
                attachments = post['attachments']['data']
                all_attachments.extend(process_attachments(attachments))

        url = data.get('paging', {}).get('next')

    return all_attachments

def main():
    attachments = get_posts_with_attachments()
    dest_folder = 'facebook_attachments'

    for url in attachments:
        download_file(url, dest_folder)

if __name__ == "__main__":
    main()
