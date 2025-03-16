import os
import json
import re
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from PyPDF2 import PdfWriter, PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
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

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    for element in content:
        if 'paragraph' in element:
            paragraph_elements = element.get('paragraph').get('elements', [])
            for elem in paragraph_elements:
                if 'textRun' in elem:
                    text_content = elem.get('textRun').get('content', '')
                    c.drawString(72, height - 72, text_content.strip())
                    height -= 12  # Move down each line
                    links = re.findall(r'https?://[^\s]+', text_content)
                    for link in links:
                        if 'drive.google.com' in link:
                            file_id = extract_drive_file_id(link)
                            if file_id and is_image(drive_service, file_id):
                                download_and_embed_image(c, drive_service, file_id, height)
                                height -= 100  # Adjust for image height

    c.save()
    buffer.seek(0)
    with open(f"{doc_name}.pdf", 'wb') as f:
        f.write(buffer.read())

def is_image(drive_service, file_id):
    try:
        file = drive_service.files().get(fileId=file_id, fields="mimeType").execute()
        if file['mimeType'].startswith('image/'):
            return True
    except HttpError as error:
        print(f"An error occurred: {error}")
    return False

def download_and_embed_image(c, drive_service, file_id, height):
    request = drive_service.files().get_media(fileId=file_id)
    file_data = request.execute()
    image = BytesIO(file_data)
    c.drawImage(image, 72, height - 100, width=200, height=100)  # Adjust size as needed

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
    parser.add_argument('--folder-id', required=True, help='The Google Drive folder ID containing the documents.')
    parser.add_argument('--credentials', required=True, help='Path to the OAuth 2.0 credentials JSON file.')
    parser.add_argument('--merge-to-pdf', action='store_true', help='Merge all documents into one PDF.')

    args = parser.parse_args()
    folder_id = args.folder_id
    credentials_file = args.credentials

    drive_service = get_service('drive', 'v3', credentials_file)
    docs_service = get_service('docs', 'v1', credentials_file)

    documents_metadata = list_documents_in_folder(drive_service, folder_id)
    pdf_files = []

    for doc in documents_metadata:
        pdf_name = f"{doc['name']}.pdf"
        download_document_as_pdf(docs_service, drive_service, doc['id'], doc['name'])
        pdf_files.append(pdf_name)

    if args.merge_to_pdf:
        merge_pdfs(pdf_files, 'merged_documents.pdf')
        print("All documents have been merged into 'merged_documents.pdf'.")

if __name__ == '__main__':
    main()

