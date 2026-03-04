#!/usr/bin/env python3
"""
create_gdoc.py — Create and populate Google Docs programmatically.

A general-purpose utility for creating Google Docs with formatted content
including headings, paragraphs, bold text, and tables via the Google Docs API.

Setup (one-time):
    1. Go to https://console.cloud.google.com
    2. Create a project (or select an existing one)
    3. Enable "Google Docs API" and "Google Drive API":
       APIs & Services -> Library -> search and enable each
    4. Create OAuth 2.0 credentials:
       APIs & Services -> Credentials -> Create Credentials -> OAuth client ID
       Application type: Desktop app
    5. Download the JSON file and save it to:
       ~/.config/google/credentials.json
       (or set GOOGLE_CREDENTIALS_PATH env var, or pass --credentials)

Usage:
    # Create a doc from a JSON content file
    pipenv run python python/create_gdoc.py --from-json content.json

    # Create a simple doc with a title
    pipenv run python python/create_gdoc.py --title "My Document"

    # Place the doc in a specific Google Drive folder
    pipenv run python python/create_gdoc.py --title "Report" --folder-id 1aBcDeFgHiJkLmNoPqRsT

    # Use a different credentials file
    pipenv run python python/create_gdoc.py --credentials ./my-creds.json --from-json data.json

JSON content file format:
    {
      "title": "Document Title",
      "content": [
        {"type": "heading1", "text": "Section Title"},
        {"type": "heading2", "text": "Subsection"},
        {"type": "paragraph", "text": "Normal paragraph text."},
        {"type": "bold_line", "text": "This line will be bold."},
        {"type": "key_value", "key": "Name", "value": "John Doe"},
        {"type": "table", "headers": ["Col A", "Col B"], "rows": [["a1", "b1"], ["a2", "b2"]]},
        {"type": "blank_line"}
      ]
    }

How it works:
    The Google Docs API uses a "batchUpdate" model where you send a list of
    insert/format requests. Text is inserted at a character index (starting at 1,
    since index 0 is the document root). After each insertion, the index advances
    by the length of the inserted text.

    Tables are inserted as structural elements. Each cell contains a paragraph,
    and the index math accounts for the overhead of table/row/cell markers.

    Authentication uses OAuth 2.0 with a local browser flow. On first run, a
    browser window opens for consent. The resulting token is cached locally so
    subsequent runs don't require re-authentication.

Token storage:
    ~/.config/google/token_gdoc.json (auto-created on first auth)
"""

import argparse
import json
import os
import sys

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("Missing Google API dependencies. Install with:")
    print("  pipenv install google-api-python-client google-auth-oauthlib google-auth-httplib2")
    sys.exit(1)

# OAuth scopes: documents for creating/editing docs, drive.file for moving to folders.
# drive.file only grants access to files this app creates, not all Drive files.
SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]

DEFAULT_CREDS_PATH = os.path.expanduser("~/.config/google/credentials.json")
DEFAULT_TOKEN_PATH = os.path.expanduser("~/.config/google/token_gdoc.json")


# =============================================================================
# Authentication
# =============================================================================

def get_credentials(creds_path=None, token_path=None):
    """
    Authenticate with Google APIs via OAuth 2.0.

    Flow:
    1. Check for a cached token file (from a previous run)
    2. If the token exists but is expired, refresh it
    3. If no token exists, launch a browser-based OAuth consent flow
    4. Cache the new token for future runs

    Args:
        creds_path: Path to the OAuth client credentials JSON file
                    (downloaded from Google Cloud Console)
        token_path: Path to cache the user's access/refresh token

    Returns:
        google.oauth2.credentials.Credentials object
    """
    creds_path = creds_path or os.environ.get("GOOGLE_CREDENTIALS_PATH", DEFAULT_CREDS_PATH)
    token_path = token_path or os.environ.get("GOOGLE_TOKEN_PATH", DEFAULT_TOKEN_PATH)

    creds = None

    # Step 1: Try loading cached token
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # Step 2: Refresh or re-authenticate if needed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Token expired but we have a refresh token — silently refresh
            creds.refresh(Request())
        else:
            # No valid token — need interactive OAuth consent
            if not os.path.exists(creds_path):
                print(f"Error: OAuth credentials file not found at: {creds_path}")
                print()
                print("To set up credentials:")
                print("  1. Go to https://console.cloud.google.com")
                print("  2. APIs & Services -> Credentials -> Create Credentials -> OAuth client ID")
                print("  3. Application type: Desktop app")
                print(f"  4. Download JSON and save to: {creds_path}")
                sys.exit(1)

            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)

        # Step 3: Cache the token
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return creds


# =============================================================================
# Document Builder
# =============================================================================

class GoogleDocBuilder:
    """
    Builds a list of Google Docs API batchUpdate requests.

    The Google Docs API works by sending a sequence of requests that modify
    the document. Text is inserted at specific character indices. This class
    tracks the current index and provides high-level methods for inserting
    formatted content.

    Index tracking:
        - The document body starts at index 1 (index 0 is the document root)
        - Each character of inserted text advances the index by 1
        - Newlines count as 1 character
        - Tables have structural overhead (table/row/cell markers)

    Usage:
        builder = GoogleDocBuilder()
        builder.add_heading("My Title")
        builder.add_paragraph("Hello world.")
        builder.add_table(["Name", "Age"], [["Alice", "30"], ["Bob", "25"]])
        requests = builder.get_requests()
    """

    def __init__(self):
        self._requests = []
        self._idx = 1  # Current insertion index (doc body starts at 1)

    def get_requests(self):
        """Return the accumulated list of API requests."""
        return self._requests

    def _insert_text(self, text):
        """Insert raw text at the current index and advance."""
        self._requests.append({
            "insertText": {
                "location": {"index": self._idx},
                "text": text,
            }
        })
        end = self._idx + len(text)
        self._idx = end
        return self._idx - len(text), end  # start, end indices

    def _apply_text_style(self, start, end, **style_fields):
        """
        Apply text styling (bold, fontSize, foregroundColor, etc.) to a range.

        The 'fields' mask tells the API which properties to update.
        Unmentioned properties are left unchanged.
        """
        if not style_fields:
            return
        self._requests.append({
            "updateTextStyle": {
                "range": {"startIndex": start, "endIndex": end},
                "textStyle": style_fields,
                "fields": ",".join(style_fields.keys()),
            }
        })

    def _apply_paragraph_style(self, start, end, **style_fields):
        """Apply paragraph styling (namedStyleType for headings, alignment, etc.)."""
        if not style_fields:
            return
        self._requests.append({
            "updateParagraphStyle": {
                "range": {"startIndex": start, "endIndex": end},
                "paragraphStyle": style_fields,
                "fields": ",".join(style_fields.keys()),
            }
        })

    # --- High-level insertion methods ---

    def add_heading(self, text, level=1):
        """
        Insert a heading. Levels 1-6 map to HEADING_1 through HEADING_6.

        Google Docs named styles: HEADING_1, HEADING_2, ..., HEADING_6
        These control font size, weight, and spacing automatically.
        """
        style_name = f"HEADING_{min(max(level, 1), 6)}"
        start, end = self._insert_text(text + "\n")
        self._apply_paragraph_style(start, end, namedStyleType=style_name)

    def add_paragraph(self, text):
        """Insert a normal paragraph of text."""
        self._insert_text(text + "\n")

    def add_bold_line(self, text):
        """Insert a single bold line."""
        start, end = self._insert_text(text + "\n")
        self._apply_text_style(start, end - 1, bold=True)  # -1 to exclude newline

    def add_key_value(self, key, value):
        """Insert a 'Key: Value' line where the key is bold."""
        start, _ = self._insert_text(f"{key}: ")
        key_end = self._idx
        self._apply_text_style(start, key_end - 1, bold=True)
        self._insert_text(value + "\n")

    def add_blank_line(self):
        """Insert an empty line for spacing."""
        self._insert_text("\n")

    def add_table(self, headers, rows):
        """
        Insert a table with a header row and data rows.

        How table indexing works in the Google Docs API:
            After an insertTable request, the document structure looks like:

            [table_start]        +1
              [row_start]        +1 per row
                [cell_start]     +1 per cell
                  [paragraph]    +1 (contains cell text + implicit newline)
                [/cell]
              [/row]
            [/table]

            To insert text into a cell, we calculate the index by walking
            through this structure: table_start -> row -> cell -> paragraph.

            Each empty cell paragraph has an implicit newline character, so
            even empty cells consume 1 index position.

        Args:
            headers: List of column header strings
            rows:    List of lists — each inner list is one row of cell values
        """
        n_rows = len(rows) + 1  # +1 for header row
        n_cols = len(headers)

        # Insert the table structure
        self._requests.append({
            "insertTable": {
                "rows": n_rows,
                "columns": n_cols,
                "location": {"index": self._idx},
            }
        })

        # Walk through the table structure to insert cell text
        cell_idx = self._idx + 1  # +1 for table start marker
        for r in range(n_rows):
            cell_idx += 1  # +1 for row start marker
            row_data = headers if r == 0 else rows[r - 1]
            for c in range(n_cols):
                cell_idx += 1  # +1 for cell start marker
                cell_idx += 1  # +1 for paragraph start within cell
                cell_text = str(row_data[c]) if c < len(row_data) else ""
                if cell_text:
                    self._requests.append({
                        "insertText": {
                            "location": {"index": cell_idx},
                            "text": cell_text,
                        }
                    })
                    # Bold the header row, smaller font for all cells
                    style = {"fontSize": {"magnitude": 9, "unit": "PT"}}
                    if r == 0:
                        style["bold"] = True
                    self._requests.append({
                        "updateTextStyle": {
                            "range": {"startIndex": cell_idx, "endIndex": cell_idx + len(cell_text)},
                            "textStyle": style,
                            "fields": ",".join(style.keys()),
                        }
                    })
                    cell_idx += len(cell_text)
                cell_idx += 1  # +1 for paragraph end (implicit newline in cell)

        self._idx = cell_idx
        # Add spacing after the table
        self._insert_text("\n")


# =============================================================================
# Content loading
# =============================================================================

def build_from_json(json_path):
    """
    Build document requests from a JSON content file.

    Expected JSON format:
    {
      "title": "Document Title",
      "content": [
        {"type": "heading1", "text": "..."},
        {"type": "heading2", "text": "..."},
        {"type": "heading3", "text": "..."},
        {"type": "paragraph", "text": "..."},
        {"type": "bold_line", "text": "..."},
        {"type": "key_value", "key": "Label", "value": "Data"},
        {"type": "table", "headers": [...], "rows": [[...], ...]},
        {"type": "blank_line"}
      ]
    }

    Returns:
        (title, requests) tuple
    """
    with open(json_path) as f:
        data = json.load(f)

    title = data.get("title", "Untitled Document")
    builder = GoogleDocBuilder()

    for item in data.get("content", []):
        item_type = item.get("type", "")

        if item_type.startswith("heading"):
            # heading1, heading2, ..., heading6
            level = int(item_type[-1]) if item_type[-1].isdigit() else 1
            builder.add_heading(item["text"], level=level)
        elif item_type == "paragraph":
            builder.add_paragraph(item["text"])
        elif item_type == "bold_line":
            builder.add_bold_line(item["text"])
        elif item_type == "key_value":
            builder.add_key_value(item["key"], item["value"])
        elif item_type == "table":
            builder.add_table(item["headers"], item["rows"])
        elif item_type == "blank_line":
            builder.add_blank_line()
        else:
            print(f"Warning: unknown content type '{item_type}', treating as paragraph")
            builder.add_paragraph(item.get("text", ""))

    return title, builder.get_requests()


def build_placeholder():
    """Build a minimal placeholder document (used when no --from-json is given)."""
    builder = GoogleDocBuilder()
    builder.add_heading("New Document")
    builder.add_paragraph("This document was created with create_gdoc.py.")
    builder.add_paragraph("To populate it with content, use --from-json with a JSON content file.")
    builder.add_blank_line()
    builder.add_heading("Example Table", level=2)
    builder.add_table(
        ["Column A", "Column B", "Column C"],
        [["Row 1A", "Row 1B", "Row 1C"], ["Row 2A", "Row 2B", "Row 2C"]],
    )
    return builder.get_requests()


# =============================================================================
# Document creation
# =============================================================================

def create_google_doc(title, requests, folder_id=None, creds_path=None):
    """
    Create a Google Doc and populate it with the given requests.

    Steps:
    1. Authenticate with Google APIs
    2. Create an empty document via the Docs API
    3. Optionally move it to a Drive folder
    4. Send batchUpdate with all the formatting/content requests
    5. Return the document URL

    Args:
        title:      Document title (shown in Google Drive)
        requests:   List of Google Docs API batchUpdate requests
        folder_id:  Optional Google Drive folder ID to move the doc into
        creds_path: Optional path to OAuth credentials JSON

    Returns:
        URL of the created document
    """
    creds = get_credentials(creds_path)

    # Build API service clients
    docs_service = build("docs", "v1", credentials=creds)
    drive_service = build("drive", "v3", credentials=creds)

    # Step 1: Create empty document
    doc = docs_service.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]
    print(f"Created: {title}")
    print(f"Doc ID:  {doc_id}")

    # Step 2: Move to folder if requested
    if folder_id:
        file_meta = drive_service.files().get(fileId=doc_id, fields="parents").execute()
        prev_parents = ",".join(file_meta.get("parents", []))
        drive_service.files().update(
            fileId=doc_id,
            addParents=folder_id,
            removeParents=prev_parents,
            fields="id, parents",
        ).execute()
        print(f"Moved to folder: {folder_id}")

    # Step 3: Populate with content
    if requests:
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": requests},
        ).execute()
        print(f"Inserted {len(requests)} formatting requests")

    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
    print(f"URL:     {doc_url}")
    return doc_url


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Create and populate a Google Doc.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  %(prog)s --title "Meeting Notes"
  %(prog)s --from-json report.json
  %(prog)s --from-json data.json --folder-id 1aBcDeFg --title "Q4 Report"
  %(prog)s --credentials ./creds.json --from-json content.json
        """,
    )
    parser.add_argument("--title", help="Document title (overrides title in JSON)")
    parser.add_argument("--from-json", metavar="FILE",
                        help="JSON file with document content (see --help for format)")
    parser.add_argument("--folder-id", help="Google Drive folder ID to place the doc in")
    parser.add_argument("--credentials", help="Path to OAuth credentials.json file")
    args = parser.parse_args()

    try:
        if args.from_json:
            json_title, requests = build_from_json(args.from_json)
            title = args.title or json_title
        else:
            title = args.title or "Untitled Document"
            requests = build_placeholder()

        url = create_google_doc(title, requests, args.folder_id, args.credentials)
        print(f"\nDone! Open your doc at:\n{url}")

    except HttpError as e:
        print(f"Google API error: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"File not found: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
