#!/usr/bin/env python3

import requests
from io import BytesIO

# Constants for your services
FACEBOOK_ACCESS_TOKEN = 'YOUR_FACEBOOK_ACCESS_TOKEN'
WORDPRESS_URL = 'http://yourwordpresssite.com'
WORDPRESS_USERNAME = 'your_wp_username'
WORDPRESS_PASSWORD = 'your_wp_password'

def download_facebook_image(facebook_image_url):
    """Download an image from a Facebook URL."""
    response = requests.get(facebook_image_url, stream=True)
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"Failed to download image: {response.status_code}")

def upload_image_to_wordpress(image_data, image_name):
    """Upload an image to a WordPress site."""
    endpoint = f"{WORDPRESS_URL}/wp-json/wp/v2/media"
    headers = {
        'Content-Disposition': f'attachment; filename={image_name}',
    }

    # Make an authenticated request
    with requests.Session() as session:
        session.auth = (WORDPRESS_USERNAME, WORDPRESS_PASSWORD)
        response = session.post(endpoint, headers=headers, files={'file': (image_name, BytesIO(image_data))})

    if response.status_code == 201:
        return response.json()
    else:
        raise Exception(f"Failed to upload image to WordPress: {response.status_code}")

def add_image_to_post(image_id, post_id):
    """Attach uploaded image to a WordPress post."""
    endpoint = f"{WORDPRESS_URL}/wp-json/wp/v2/posts/{post_id}"
    data = {
        'featured_media': image_id
    }

    with requests.Session() as session:
        session.auth = (WORDPRESS_USERNAME, WORDPRESS_PASSWORD)
        response = session.post(endpoint, json=data)

    if response.status_code == 200:
        print("Image successfully attached to post.")

def main(facebook_image_url, post_id):
    # Download the image from Facebook
    image_data = download_facebook_image(facebook_image_url)

    # Upload image to WordPress
    image_name = 'uploaded_facebook_image.jpg' # replace with a suitable file name
    image_info = upload_image_to_wordpress(image_data, image_name)

    # Attach the uploaded image to a WordPress post
    image_id = image_info.get('id')
    add_image_to_post(image_id, post_id)

if __name__ == "__main__":
    facebook_image_url = 'FACEBOOK_PHOTO_URL'  # Replace with the actual Facebook image URL
    wordpress_post_id = 123  # Replace with the actual WordPress post ID
    main(facebook_image_url, wordpress_post_id)

