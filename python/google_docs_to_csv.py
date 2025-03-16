import os
import json
import csv
import argparse
import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def parseargs():
    parser = argparse.ArgumentParser(
        description="Fetch Google Docs and convert to CSV/JSON."
    )
    parser.add_argument(
        "--folder-id",
        default=os.environ.get("GDRIVE_FOLDER_ID"),
        help="The Google Drive folder ID containing the documents.",
    )
    parser.add_argument(
        "--folder-name",
        default=os.environ.get("GDRIVE_FOLDER_NAME"),
        help="The Google Drive folder Name containing the documents.",
    )
    parser.add_argument(
        "--credentials",
        default=os.environ.get("GOOGLE_OAUTH_CREDS", "credentials.json"),
        help="Path to the OAuth 2.0 credentials JSON file.",
    )

    return parser.parse_args()


def get_oauth_token(scopes, credentials_file="credentials.json"):
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", scopes)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, scopes)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds


def get_service(api_name, api_version, scopes, credentials_file):
    # creds = Credentials.from_authorized_user_file(credentials_file, scopes)
    creds = get_oauth_token(scopes, credentials_file=credentials_file)
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
        results = (
            service.files()
            .list(q=query, fields="nextPageToken, files(id, name)")
            .execute()
        )
        files = results.get("files", [])
        next_page_token = results.get("nextPageToken")
        while next_page_token:
            results = (
                service.files()
                .list(
                    pageToken=next_page_token,
                    q=query,
                    fields="nextPageToken, files(id, name)",
                )
                .execute()
            )
            files.extend(results.get("files", []))
            next_page_token = results.get("nextPageToken")
        return files

    except HttpError as error:
        print(f"An error occurred: {error}")
        return []


def get_document_content(docs_service, document_id):
    try:
        document = docs_service.documents().get(documentId=document_id).execute()
        content = document.get("body").get("content")
        text = ""
        for element in content:
            if "paragraph" in element:
                paragraph_elements = element.get("paragraph").get("elements")
                for elem in paragraph_elements:
                    if "textRun" in elem:
                        text += elem.get("textRun").get("content")
        return text.strip()
    except HttpError as error:
        print(f"An error occurred: {error}")
        return ""


def save_to_json(documents, filename="documents.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(documents, f, ensure_ascii=False, indent=4)


def save_to_csv(documents, filename="documents.csv"):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Content"])
        for doc in documents:
            writer.writerow([doc["name"], doc["content"]])


def main():
    args = parseargs()
    folder_id = args.folder_id
    folder_name = args.folder_name
    credentials_file = args.credentials
    SCOPES = [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/documents.readonly",
    ]

    drive_service = get_service("drive","v3", SCOPES, credentials_file=credentials_file)
    docs_service = get_service("docs", "v1", SCOPES, credentials_file=credentials_file)

    if not folder_id and folder_name:
        folder_id = get_folder_id(drive_service, folder_name)
        print(f"folder_id = {folder_id}")
    else:
        print("Need either a folder ID or folder name.")
        exit(1)
    documents_metadata = list_documents_in_folder(drive_service, folder_id)
    documents = []

    for doc in documents_metadata:
        if doc["name"] == "Facebook Post: 2024-11-22T20:57:24":
            print(doc["name"])
        content = get_document_content(docs_service, doc["id"])
        documents.append({"name": doc["name"], "content": content})

    save_to_json(documents)
    save_to_csv(documents)


if __name__ == "__main__":
    main()
