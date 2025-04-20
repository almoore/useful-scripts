import os
import json
import re
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from PyPDF2 import PdfWriter, PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PIL import Image
from io import BytesIO
import argparse

# Define the scopes required
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/documents.readonly'
]

def get_service(api_name, api_version, credentials_file, token_file='token.json'):
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
    return build(api_name, api_version, credentials=creds)


def get_folder_id(service, folder_name):
    results = (
        service.files()
        .list(
            q=f"mimeType = 'application/vnd.google-apps.folder' and name = '{folder_name}'",
            pageSize=10,
            fields="nextPageToken, files(id, name)",
        )
        .execute()
    )
    folder_id_result = results.get("files", [])
    return folder_id_result[0].get("id")


def list_documents_in_folder(service, folder_id):
    try:
        query = f"'{folder_id}' in parents and mimeType = 'application/vnd.google-apps.document'"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        return results.get('files', [])
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []

def download_document_as_pdf(docs_service, drive_service, doc_id, doc_name):
    document = docs_service.documents().get(documentId=doc_id).execute()
    content = document.get('body').get('content')

    buffer = canvas.Canvas(f"{doc_name}.pdf", pagesize=letter)
    width, height = letter
    text_obj = buffer.beginText(40, height - 40)

    for element in content:
        if 'paragraph' in element:
            paragraph_elements = element.get('paragraph').get('elements', [])
            for elem in paragraph_elements:
                if 'textRun' in elem:
                    text_content = elem.get('textRun').get('content', '')
                    text_obj.textLines(text_content.strip())
                    link = elem.get("textRun").get("textStyle", {}).get("link", {})
                    links = re.findall(r'https?://[^\s]+', text_content)
                    if link:
                        links.append(link.get('url'))
                    for link in links:
                        if 'drive.google.com' in link:
                            file_id = extract_drive_file_id(link)
                            if file_id and is_image(drive_service, file_id):
                                download_and_embed_image(buffer, drive_service, file_id, 40, text_obj.getY() - 20)
                                text_obj.moveCursor(0, -120)

        buffer.drawText(text_obj)
    buffer.save()

def is_image(drive_service, file_id):
    try:
        file = drive_service.files().get(fileId=file_id, fields="mimeType").execute()
        return file['mimeType'].startswith('image/')
    except HttpError as error:
        print(f"An error occurred: {error}")
    return False


def download_and_embed_image(c, drive_service, file_id, xpos, ypos,
                             max_width=552, max_height=732):
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
        final_ypos = ypos - height  # Adjust position

        c.drawImage(temp_image_path, xpos, final_ypos, width=width,
                    height=height, mask='auto')

    except HttpError as error:
        print(f"An error occurred: {error}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def extract_drive_file_id(url):
    match = re.search(r'/d/([A-Za-z0-9_-]+)', url)
    if match:
        return match.group(1)
    return None

def merge_pdfs(pdf_files, output_path):
    pdf_writer = PdfWriter()
    for pdf_file in pdf_files:
        with open(pdf_file, 'rb') as f:
            pdf_reader = PdfReader(f)
            for page in range(len(pdf_reader.pages)):
                pdf_writer.add_page(pdf_reader.pages[page])
    with open(output_path, 'wb') as f:
        pdf_writer.write(f)

def main():
    parser = argparse.ArgumentParser(description='Fetch Google Docs, convert links to embedded images, and convert to PDF.')
    parser.add_argument('--folder-id', help='The Google Drive folder ID containing the documents.')
    parser.add_argument(
        "--folder-name",
        default=os.environ.get("GDRIVE_FOLDER_NAME"),
        help="The Google Drive folder Name containing the documents.",
    )
    parser.add_argument("--limit", type=int, default=0, help="Download a set limit of pages.")
    parser.add_argument('--credentials', default='credentials.json', help='Path to the OAuth 2.0 credentials JSON file.')
    parser.add_argument('--merge-to-pdf', action='store_true', help='Merge all documents into one PDF.')

    args = parser.parse_args()
    folder_id = args.folder_id
    folder_name = args.folder_name
    credentials_file = args.credentials
    limit = args.limit

    drive_service = get_service('drive', 'v3', credentials_file)
    docs_service = get_service('docs', 'v1', credentials_file)

    if not folder_id and folder_name:
        folder_id = get_folder_id(drive_service, folder_name)
        print(f"folder_id = {folder_id}")
    else:
        print("Need either a folder ID or folder name.")
        exit(1)

    documents_metadata = list_documents_in_folder(drive_service, folder_id)
    pdf_files = []
    if limit:
        documents_metadata = documents_metadata[:limit]

    for doc in documents_metadata:
        pdf_name = f"{doc['name']}.pdf"
        download_document_as_pdf(docs_service, drive_service, doc['id'], doc['name'])
        pdf_files.append(pdf_name)

    if args.merge_to_pdf:
        merge_pdfs(pdf_files, 'merged_documents.pdf')
        print("All documents have been merged into 'merged_documents.pdf'.")

if __name__ == '__main__':
    main()

