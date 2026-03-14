import base64
import os
import time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.file",
]

BASE_DIR = os.path.dirname(__file__)
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")


def authenticate() -> Credentials:
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return creds


def build_gmail_service(creds: Credentials):
    return build("gmail", "v1", credentials=creds)


def search_emails(service, keywords: list) -> list:
    """
    Search Gmail for emails whose subject contains ALL specified keywords.
    Looks back 25 hours to cover any gap between daily runs.
    """
    keyword_query = " ".join(f'"{kw}"' for kw in keywords)
    # 25 hours in seconds = 90000
    after_timestamp = int(time.time()) - 90000
    query = f"subject:({keyword_query}) after:{after_timestamp} has:attachment"

    messages = []
    response = service.users().messages().list(userId="me", q=query).execute()
    messages.extend(response.get("messages", []))

    while "nextPageToken" in response:
        response = (
            service.users()
            .messages()
            .list(userId="me", q=query, pageToken=response["nextPageToken"])
            .execute()
        )
        messages.extend(response.get("messages", []))

    return messages


def get_pdf_attachments(service, message_id: str) -> list:
    """
    Returns a list of dicts:
      { filename, data (bytes), message_id, attachment_id }
    for every PDF attachment in the given message.
    """
    msg = service.users().messages().get(userId="me", id=message_id).execute()
    parts = _get_parts(msg.get("payload", {}))
    attachments = []

    for part in parts:
        filename = part.get("filename", "")
        if not filename.lower().endswith(".pdf"):
            continue
        body = part.get("body", {})
        attachment_id = body.get("attachmentId")
        if not attachment_id:
            continue
        att = (
            service.users()
            .messages()
            .attachments()
            .get(userId="me", messageId=message_id, id=attachment_id)
            .execute()
        )
        data = base64.urlsafe_b64decode(att["data"])
        attachments.append(
            {
                "filename": filename,
                "data": data,
                "message_id": message_id,
                "attachment_id": attachment_id,
            }
        )

    return attachments


def _get_parts(payload: dict) -> list:
    parts = []
    if payload.get("mimeType", "").startswith("multipart"):
        for part in payload.get("parts", []):
            parts.extend(_get_parts(part))
    else:
        parts.append(payload)
    return parts
