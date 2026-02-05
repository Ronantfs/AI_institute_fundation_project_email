from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send"
]

# HARD-CODED absolute paths so can use with MCP client and direct invoke easily (being lazy)
TOKEN_FILE = "/Users/ronantwomweyfriedlander/Desktop/code/KL/CV CODE REPOS/AI_institute_fundation_project_email/token.json"
CLIENT_SECRET_FILE = "/Users/ronantwomweyfriedlander/Desktop/code/KL/CV CODE REPOS/AI_institute_fundation_project_email/gmail_credentials.json"


def get_gmail_service():
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE,
                SCOPES,
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)
