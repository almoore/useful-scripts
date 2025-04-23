#!/usr/bin/env python3

import requests
import argparse
import os
from io import BytesIO
from datetime import datetime
from urllib.parse import urlparse


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


def add_image_to_post(
    image_id, post_id, wordpress_url, wordpress_username, wordpress_password
):
    """Attach uploaded image to a WordPress post."""
    endpoint = f"{wordpress_url}/wp-json/wp/v2/posts/{post_id}"
    data = {"featured_media": image_id}

    with requests.Session() as session:
        session.auth = (wordpress_username, wordpress_password)
        response = session.post(endpoint, json=data)

    if response.status_code == 200:
        print("Image successfully attached to post.")


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


def main():
    args = parseargs()
    facebook_image_url = args.image
    wordpress_post_id = args.post
    site_url = args.url
    username = args.user
    password = args.password
    access_token = args.access_token
    file = args.file
    image_info = {}
    if site_url and "wordpress.com" in site_url:
        site_id = get_wordpress_com_site_id(site_url, access_token)
    if facebook_image_url:
        # Download the image from Facebook
        image_data = download_facebook_image(facebook_image_url)

        # Upload image to WordPress
        image_name = "uploaded_facebook_image.jpg"  # replace with a suitable file name
        image_info = upload_image_to_wordpress(image_data, image_name)
    if file:
        image_info = upload_image_to_wordpress_com(
            access_token=access_token, site_id=site_id, image_path=file
        )

    # Attach the uploaded image to a WordPress post
    image_id = image_info.get("id")
    add_image_to_post(image_id, wordpress_post_id, site_url, username, password)


if __name__ == "__main__":
    main()
