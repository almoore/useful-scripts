import requests


def upload_image_to_wordpress_com(access_token, site_id, image_path):
    url = f'https://public-api.wordpress.com/rest/v1.1/sites/{site_id}/media/new'

    with open(image_path, 'rb') as img_file:
        headers = {
            'Authorization': f'Bearer {access_token}',
        }
        files = {
            'media': img_file,
        }
        response = requests.post(url, headers=headers, files=files)

    if response.status_code == 201:
        print("Upload successful:", response.json())
    else:
        print("Upload failed:", response.status_code, response.text)


# Example usage
site_id = 'your-site-id'
access_token = 'your-oauth2-access-token'
image_path = 'path/to/your/image.jpg'

upload_image_to_wordpress_com(access_token, site_id, image_path)
