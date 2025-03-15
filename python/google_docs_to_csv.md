# Google Docs to CSV
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

[google_docs_to_csv.py](google_docs_to_csv.py)
