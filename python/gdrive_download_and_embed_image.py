from PIL import Image
from io import BytesIO
import requests

def download_and_embed_image(c, drive_service, file_id, xpos, ypos, max_width=552, max_height=732):
    try:
        # Fetch image data from Google Drive
        request = drive_service.files().get_media(fileId=file_id)
        file_data = request.execute()
        
        # Use PIL to open the image from bytes
        image = Image.open(BytesIO(file_data))
        
        # Determine the aspect ratio
        original_width, original_height = image.size
        aspect_ratio = original_width / original_height

        # Calculate dimensions that maintain aspect ratio
        if original_width > original_height:
            # Landscape orientation: fit width first
            width = min(max_width, original_width)
            height = width / aspect_ratio
            if height > max_height:  # Adjust if height exceeds max
                height = max_height
                width = height * aspect_ratio
        else:
            # Portrait orientation: fit height first
            height = min(max_height, original_height)
            width = height * aspect_ratio
            if width > max_width:  # Adjust if width exceeds max
                width = max_width
                height = width / aspect_ratio

        # Save the image temporarily to a file
        temp_image_path = '/tmp/temp_image.jpg'  # Adjust path as needed
        image.save(temp_image_path)

        # Draw image on canvas
        final_xpos = xpos
        final_ypos = ypos - height  # Adjust position

        c.drawImage(temp_image_path, final_xpos, final_ypos, width=width, height=height, mask='auto')

    except HttpError as error:
        print(f"An error occurred: {error}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

