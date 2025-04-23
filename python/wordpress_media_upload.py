import requests
import os


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


# Example usage
access_token = os.environ.get("ACCESS_TOKEN")
site_url = os.environ.get("SITE_URL")
site_id = get_wordpress_com_site_id(site_url, access_token)
print(f"site_id: {site_id}")
image_path = os.environ.get("IMAGE_PATH", "image.jpg")  # path to your image.jpg

upload_image_to_wordpress_com(access_token, site_id, image_path)
