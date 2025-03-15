"""
To convert the contents of a Google Docs folder into a CSV or JSON file, you'll need to use Google APIs, specifically the Google Drive API to list the documents in the folder and the Google Docs API to access their contents. Here’s a step-by-step guide:

### Prerequisites

1. **Google Cloud Project**: Set up a Google Cloud project and enable the Google Drive API and Google Docs API.

2. **OAuth Credentials**: Create OAuth 2.0 credentials and download the JSON file for use in your script.

3. **Python Environment**: Install the necessary libraries using pip:
   ```bash
   pip install google-auth google-auth-oauthlib google-auth-httplib2 google-auth google-api-python-client
   ```

### Explanation

- **Authentication**: The script uses OAuth2 credentials stored in a JSON file to authenticate and access your Google Drive and Docs.

- **Listing Files in a Folder**: The Drive API is used to list Google Docs files in a specified folder (`FOLDER_ID`).

- **Reading Document Content**: The Docs API is utilized to read the content of each document. This example concatenates the text of each document’s paragraphs.

- **Saving Data**: Two functions are provided to save the content as either a JSON or CSV file. Adjust these functions as needed to customize your output format.

### Considerations

- **Error Handling**: Always incorporate error handling to manage API request errors and edge cases.

- **Quota and Permissions**: Be mindful of your API quotas and ensure your application follows Google's use policy for accessing and handling documents.

- **Sensitive Data**: Ensure sensitive data like credentials are securely stored and handled.

By utilizing these APIs, this script provides a framework to convert Google Docs contents into standard data formats for further processing or analysis.

### Python Script

This script will list documents in a Google Drive folder and retrieve their contents. You can parse this content and save it as a CSV or JSON file.


"""

import os
import json
import csv
import argparse
import google.auth
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def parseargs():
    parser = argparse.ArgumentParser(
        description='Fetch Google Docs and convert to CSV/JSON.')
    parser.add_argument('--folder-id', required=True,
                        help='The Google Drive folder ID containing the documents.')
    parser.add_argument('--credentials', required=True,
                        help='Path to the OAuth 2.0 credentials JSON file.')

    return parser.parse_args()


def get_service(api_name, api_version, *scopes, credentials_file):
    creds = Credentials.from_authorized_user_file(credentials_file, scopes)
    return build(api_name, api_version, credentials=creds)


def list_documents_in_folder(service, folder_id):
    try:
        query = f"'{folder_id}' in parents and mimeType = 'application/vnd.google-apps.document'"
        results = service.files().list(q=query,
                                       fields="files(id, name)").execute()
        return results.get('files', [])
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []


def get_document_content(docs_service, document_id):
    try:
        document = docs_service.documents().get(
            documentId=document_id).execute()
        content = document.get('body').get('content')
        text = ''
        for element in content:
            if 'paragraph' in element:
                paragraph_elements = element.get('paragraph').get('elements')
                for elem in paragraph_elements:
                    if 'textRun' in elem:
                        text += elem.get('textRun').get('content')
        return text.strip()
    except HttpError as error:
        print(f"An error occurred: {error}")
        return ''


def save_to_json(documents, filename='documents.json'):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(documents, f, ensure_ascii=False, indent=4)


def save_to_csv(documents, filename='documents.csv'):
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Name', 'Content'])
        for doc in documents:
            writer.writerow([doc['name'], doc['content']])


def main():
    args = parseargs()
    folder_id = args.folder_id
    credentials_file = args.credentials

    drive_service = get_service('drive', 'v3',
                                'https://www.googleapis.com/auth/drive.readonly',
                                credentials_file=credentials_file)
    docs_service = get_service('docs', 'v1',
                               'https://www.googleapis.com/auth/documents.readonly',
                               credentials_file=credentials_file)

    documents_metadata = list_documents_in_folder(drive_service, folder_id)
    documents = []

    for doc in documents_metadata:
        content = get_document_content(docs_service, doc['id'])
        documents.append({'name': doc['name'], 'content': content})

    save_to_json(documents)
    save_to_csv(documents)


if __name__ == '__main__':
    main()
