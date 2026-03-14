import io

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


def build_drive_service(creds: Credentials):
    return build("drive", "v3", credentials=creds)


def create_subfolder(service, name: str, parent_id: str) -> str:
    """Creates a subfolder under parent_id and returns the new folder's ID."""
    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def upload_pdf(service, filename: str, data: bytes, folder_id: str) -> str:
    """Uploads PDF bytes to the specified Drive folder. Returns the new file's ID."""
    metadata = {"name": filename, "parents": [folder_id]}
    media = MediaIoBaseUpload(io.BytesIO(data), mimetype="application/pdf")
    file = (
        service.files()
        .create(body=metadata, media_body=media, fields="id")
        .execute()
    )
    return file["id"]
