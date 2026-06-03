from __future__ import annotations

import logging
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload


LOGGER = logging.getLogger(__name__)
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
EXCEL_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _build_drive_service(credentials_path: str) -> object:
    credentials_file = Path(credentials_path)
    if not credentials_file.exists():
        raise FileNotFoundError(f"Service account file not found: {credentials_file}")

    credentials = service_account.Credentials.from_service_account_file(
        str(credentials_file), scopes=SCOPES
    )
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def get_latest_excel_file(
    folder_id: str,
    credentials_path: str = "credentials/service_account.json",
    download_dir: str = "downloads",
) -> str:
    """Download the newest .xlsx file from a Google Drive folder."""

    if not folder_id:
        raise ValueError("folder_id is required")

    service = _build_drive_service(credentials_path)
    download_path = Path(download_dir)
    download_path.mkdir(parents=True, exist_ok=True)

    query = (
        f"'{folder_id}' in parents and trashed = false and "
        f"mimeType = '{EXCEL_MIME_TYPE}'"
    )

    try:
        response = (
            service.files()
            .list(
                q=query,
                fields="files(id, name, modifiedTime)",
                orderBy="modifiedTime desc",
                pageSize=1,
            )
            .execute()
        )
        files = response.get("files", [])
        if not files:
            raise FileNotFoundError("No Excel files were found in the Drive folder")

        latest_file = files[0]
        file_id = latest_file["id"]
        file_name = latest_file["name"]
        local_path = download_path / file_name

        request = service.files().get_media(fileId=file_id)
        with local_path.open("wb") as handle:
            downloader = MediaIoBaseDownload(handle, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status is not None:
                    LOGGER.info("Download progress for %s: %.0f%%", file_name, status.progress() * 100)

        LOGGER.info("Downloaded latest Excel file to %s", local_path)
        return str(local_path)
    except HttpError as exc:
        LOGGER.exception("Google Drive API request failed")
        raise RuntimeError("Failed to access Google Drive") from exc
