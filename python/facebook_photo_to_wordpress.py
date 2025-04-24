#!/usr/bin/env python3

import requests
import argparse
import os
import json
from io import BytesIO
from datetime import datetime
from urllib.parse import urlparse

from python.wordpress_media_upload import access_token


def parseargs():
    parser = argparse.ArgumentParser(
        description="Combine Facebook post data and convert to PDF."
    )
    parser.add_argument("--image", default=os.environ.get("IMAGE_PATH"))
    parser.add_argument("--post", default=os.environ.get("WORDPRESS_POST_ID"))
    parser.add_argument(
        "--export-file", help="Facebook json export file with a list of posts and media"
    )
    parser.add_argument(
        "--url",
        "-U",
        default=os.environ.get("WORDPRESS_URL"),
        help="The base URL path for the wordpress site.",
    )
    parser.add_argument(
        "--user",
        "-u",
        default=os.environ.get("WORDPRESS_USERNAME"),
        help="Wordpress username.",
    )
    parser.add_argument(
        "--password",
        "-p",
        default=os.environ.get("WORDPRESS_PASSWORD"),
        help="Wordpress password or token.",
    )
    parser.add_argument(
        "--access-token",
        "-A",
        default=os.environ.get("WORDPRESS_ACCESS_TOKEN"),
        help="Wordpress OAuth2 token.",
    )

    parser.add_argument(
        "--start-date",
        default="2005-01-01",
        help="Start date for filtering posts (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--end-date",
        default=str(datetime.now().date()),
        help="End date for filtering posts (YYYY-MM-DD).",
    )

    return parser.parse_args()


def get_post_by_title(site_id, access_token, post_title):
    """Search for a WordPress.com post by title."""
    url = f'https://public-api.wordpress.com/rest/v1.1/sites/{site_id}/posts'
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    params = {
        'search': post_title,
        'number': 1  # Limit results to optimize the lookup
    }
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        posts = response.json().get('posts')
        if posts:
            return posts[0]  # Return the first matched post
        else:
            print("No post found with the specified title.")
            return None
    else:
        print(f"Failed to retrieve posts: {response.status_code} - {response.text}")
        return None


def get_wordpress_post_content(site_id, access_token, post_id):
    """Retrieve content and media from a WordPress.com post."""
    url = f'https://public-api.wordpress.com/rest/v1.1/sites/{site_id}/posts/{post_id}'
    headers = {
        'Authorization': f'Bearer {access_token}',
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        post = response.json()
        content = post.get('content')
        media_urls = []
        attachments = post.get('attachments', {})
        for attachment in attachments.values():
            media_urls.append(attachment.get('URL'))
        return content, media_urls
    else:
        print(
            f"Failed to retrieve WordPress post: {response.status_code} - {response.text}")
        return None, None


def get_wordpress_post_content(site_id, access_token, post_id):
    """Retrieve content and media from a WordPress.com post."""
    url = f'https://public-api.wordpress.com/rest/v1.1/sites/{site_id}/posts/{post_id}'
    headers = {
        'Authorization': f'Bearer {access_token}',
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        post = response.json()
        content = post.get('content')
        media_urls = []
        attachments = post.get('attachments', {})
        for attachment in attachments.values():
            media_urls.append(attachment.get('URL'))
        return content, media_urls
    else:
        print(
            f"Failed to retrieve WordPress post: {response.status_code} - {response.text}")
        return None, None


def get_facebook_post_content(post_id, access_token):
    """Retrieve content and media from a Facebook post."""
    url = f'https://graph.facebook.com/v22.0/{post_id}'
    params = {
        'access_token': access_token,
        'fields': 'message,attachments{media}'
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        post = response.json()
        content = post.get('message', '')
        media_urls = []
        attachments = post.get('attachments', {}).get('data', [])
        for attachment in attachments:
            media = attachment.get('media', {}).get('image', {}).get('src')
            if media:
                media_urls.append(media)
        return content, media_urls
    else:
        print(
            f"Failed to retrieve Facebook post: {response.status_code} - {response.text}")
        return None, None

def compare_posts(wp_content, wp_media, fb_content, fb_media):
    """Compare the content and media from WordPress and Facebook posts."""
    text_match = wp_content.strip() == fb_content.strip()
    media_match = set(wp_media) == set(fb_media)
    return text_match, media_match


def compare_post_content(wp_content, fb_content, fb_media):
    """Compare the content and media from WordPress and Facebook posts."""
    text_match = wp_content.strip() == fb_content.strip()
    return text_match


def download_facebook_image(facebook_image_url):
    """Download an image from a Facebook URL."""
    response = requests.get(facebook_image_url, stream=True)
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"Failed to download image: {response.status_code}")


def upload_image_to_wordpress(
    image_data, image_name, wordpress_url, wordpress_username, wordpress_password
):
    """Upload an image to a WordPress site."""
    endpoint = f"{wordpress_url}/wp-json/wp/v2/media"
    headers = {
        "Content-Disposition": f"attachment; filename={image_name}",
    }

    # Make an authenticated request
    with requests.Session() as session:
        session.auth = (wordpress_username, wordpress_password)
        response = session.post(
            endpoint, headers=headers, files={"file": (image_name, BytesIO(image_data))}
        )

    if response.status_code == 201:
        return response.json()
    else:
        raise Exception(f"Failed to upload image to WordPress: {response.status_code}")


def upload_image_to_wordpress_com(access_token, site_id, image_path):
    url = f"https://public-api.wordpress.com/rest/v1.1/sites/{site_id}/media/new"

    try:
        with open(image_path, "rb") as img_file:
            headers = {
                "Authorization": f"Bearer {access_token}",
            }
            files = {
                "media[]": img_file,
            }
            response = requests.post(url, headers=headers, files=files)
        if response.status_code == 201:
            print("Upload successful:", response.json())
            return response.json()
        else:
            print("Upload failed:", response.status_code, response.text)

    except FileNotFoundError:
        print(f"The file {image_path} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


def attach_image_to_post(site_id, access_token, post_id, image_id):
    """Attach an uploaded image to a WordPress.com post."""
    url = f'https://public-api.wordpress.com/rest/v1.1/sites/{site_id}/posts/{post_id}'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    data = {
        'content': f'<img src="{image_id}" alt="Facebook Image">'
    }
    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        print("Image successfully attached to post.")
    else:
        print(f"Failed to attach image to post: {response.status_code} - {response.text}")


def upload_image_to_wordpress_com(access_token, site_id, image_path):
    url = f"https://public-api.wordpress.com/rest/v1.1/sites/{site_id}/media/new"

    try:
        with open(image_path, "rb") as img_file:
            headers = {
                "Authorization": f"Bearer {access_token}",
            }
            files = {
                "media[]": img_file,
            }
            response = requests.post(url, headers=headers, files=files)
        if response.status_code == 201:
            print("Upload successful:", response.json())
        else:
            print("Upload failed:", response.status_code, response.text)

    except FileNotFoundError:
        print(f"The file {image_path} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


def get_wordpress_com_site_id(site_url, access_token):
    """Retrieve the site ID for a given WordPress.com site URL."""
    endpoint = f"https://public-api.wordpress.com/rest/v1.1/sites/{site_url}"
    headers = {"Authorization": f"Bearer {access_token}"}

    response = requests.get(endpoint, headers=headers)

    if response.status_code == 200:
        site_data = response.json()
        return site_data.get("ID")  # The key is 'ID' in this API version
    else:
        raise Exception(
            f"Failed to retrieve site ID: {response.status_code} {response.text}"
        )


def check_path_type(path):
    """
    Checks if the given path is a file or a URL.

    Args:
        path (str): The path to check.

    Returns:
        str: "file" if the path is a file, "url" if it's a URL, or None if it's neither.
    """
    parsed_url = urlparse(path)
    if parsed_url.scheme:
        return "url"
    elif os.path.isfile(path):
        return "file"
    else:
        return None


def process_facebook_posts(wp_post_id, fb_posts, wp_site_id, wp_access_token):
    """Process each Facebook post for comparison and upload."""
    wp_content, wp_media = get_wordpress_post_content(wp_site_id, wp_access_token, wp_post_id)

    if wp_content is not None:
        for fb_post in fb_posts:
            fb_content = fb_post.get('message', '')
            fb_media = [media.get('media', {}).get('image', {}).get('src') for media in fb_post.get('attachments', {}).get('data', []) if media.get('media', {}).get('image', {}).get('src')]

            if compare_post_content(wp_content, fb_content, fb_media):
                print("Content matches. Proceeding to upload images...")
                for fb_media_url in fb_media:
                    image_id = upload_image_to_wordpress_com(wp_site_id, wp_access_token, fb_media_url)
                    if image_id:
                        attach_image_to_post(site_id=wp_site_id, access_token=wp_access_token, post_id=wp_post_id, image_id=image_id)



def main():
    args = parseargs()
    facebook_image_url = args.image
    wordpress_post_id = args.post
    site_url = args.url
    username = args.user
    password = args.password
    access_token = args.access_token
    export_file = args.export_file
    image_info = {}
    if site_url and "wordpress.com" in site_url:
        site_id = get_wordpress_com_site_id(site_url, access_token)
    if facebook_image_url:
        # Download the image from Facebook
        image_data = download_facebook_image(facebook_image_url)

        # Upload image to WordPress
        image_name = "uploaded_facebook_image.jpg"  # replace with a suitable file name
        image_info = upload_image_to_wordpress(image_data, image_name)
    if args.image:
        image_info = upload_image_to_wordpress_com(
            access_token=access_token, site_id=site_id, image_path=args.image
        )

    # Attach the uploaded image to a WordPress post
    image_id = image_info.get("id")
    attach_image_to_post(image_id, wordpress_post_id, site_url, username, password)


if __name__ == "__main__":
    main()
