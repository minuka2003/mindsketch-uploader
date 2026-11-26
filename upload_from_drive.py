"""Pulls the oldest queued MP4 from Google Drive and uploads it to YouTube via Data API v3."""
import io
import json
import socket
import os
import sys
import tempfile
import time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/drive",
]

QUEUE_FOLDER_ID = os.environ.get("DRIVE_QUEUE_FOLDER_ID", "1Vbk8tyYVgoYyZDIbXdIllpZU2pducPP7")
PUBLISHED_FOLDER_ID = os.environ.get("DRIVE_PUBLISHED_FOLDER_ID", "14r5oeekOKaaaCahDcdNhCHuZpCa4DpmZ")
DEFAULT_PRIVACY = os.environ.get("DEFAULT_PRIVACY_STATUS", "public")
MAX_UPLOADS_PER_RUN = int(os.environ.get("MAX_UPLOADS_PER_RUN", "1"))


REQUIRED_SECRETS = ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN")


def get_credentials() -> Credentials:
    missing = [k for k in REQUIRED_SECRETS if not os.environ.get(k, "").strip()]
    if missing:
        print(
            "ERROR: these GitHub secrets are empty or not set: " + ", ".join(missing)
            + "\nAdd them under Settings -> Secrets and variables -> Actions (see README step 3).",
            file=sys.stderr,
        )
        sys.exit(1)
    client_id = os.environ["GOOGLE_CLIENT_ID"].strip()
    client_secret = os.environ["GOOGLE_CLIENT_SECRET"].strip()
    refresh_token = os.environ["GOOGLE_REFRESH_TOKEN"].strip()
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds


def list_queued_files(drive):
    query = f"'{QUEUE_FOLDER_ID}' in parents and trashed = false"
    res = drive.files().list(
        q=query,
        orderBy="createdTime asc",
        fields="files(id, name, mimeType, parents, appProperties)",
        pageSize=50,
    ).execute()
    return res.get("files", [])


def download_file(drive, file_id: str, dest_path: str):
    request = drive.files().get_media(fileId=file_id)
    with io.FileIO(dest_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request, chunksize=4 * 1024 * 1024)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"Downloading... {int(status.progress() * 100)}%")


def move_to_published(drive, file_id: str, current_parents: list):
    prev = ",".join(current_parents) if current_parents else QUEUE_FOLDER_ID
    drive.files().update(
        fileId=file_id,
        addParents=PUBLISHED_FOLDER_ID,
        removeParents=prev,
        fields="id, parents",
    ).execute()


def mark_uploaded(drive, file_id: str, video_id: str):
    """Tag the Drive file with its YouTube ID so a failed move can never cause a duplicate upload."""
    drive.files().update(fileId=file_id, body={"appProperties": {"youtube_id": video_id}}).execute()


def load_metadata(drive, json_file, fallback_stem: str) -> dict:
    default_meta = {
        "title": f"{fallback_stem.replace('_', ' ').title()} #shorts",
        "description": "#shorts",
        "tags": ["shorts"],
        "category_id": "22",
        "privacy_status": DEFAULT_PRIVACY,
        "made_for_kids": False,
        "contains_synthetic_media": True,
    }
    if not json_file:
        return default_meta

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        download_file(drive, json_file["id"], tmp_path)
        with open(tmp_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        default_meta.update({k: v for k, v in data.items() if v is not None})
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    return default_meta


def upload_to_youtube(youtube, video_path: str, meta: dict) -> str:
    body = {
        "snippet": {
            "title": meta["title"][:100],
            "description": meta["description"][:5000],
            "tags": meta.get("tags", []),
            "categoryId": str(meta.get("category_id", "22")),
        },
        "status": {
            "privacyStatus": meta.get("privacy_status", DEFAULT_PRIVACY),
            "selfDeclaredMadeForKids": bool(meta.get("made_for_kids", False)),
            "containsSyntheticMedia": bool(meta.get("contains_synthetic_media", True)),
        },
    }

    media = MediaFileUpload(video_path, mimetype="video/mp4", chunksize=4 * 1024 * 1024, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    retries = 0
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                print(f"Uploading to YouTube... {int(status.progress() * 100)}%")
        except HttpError as e:
            if e.resp.status in (500, 502, 503, 504) and retries < 5:
                retries += 1
                time.sleep(2 ** retries)
                continue
            raise
        except (socket.timeout, ConnectionError, OSError) as e:
            if retries < 5:
                retries += 1
                print(f"Network error ({e}); retrying in {2 ** retries}s...")
                time.sleep(2 ** retries)
                continue
            raise

    requested = body["status"]["privacyStatus"]
    actual = response.get("status", {}).get("privacyStatus", requested)
    if requested != actual:
        print(
            f"WARNING: requested '{requested}' but YouTube set '{actual}'. If your Google Cloud project "
            "has not passed the YouTube API audit, uploads are locked to private (see README Troubleshooting).",
            file=sys.stderr,
        )
    return response["id"]


def main():
    creds = get_credentials()
    drive = build("drive", "v3", credentials=creds)
    youtube = build("youtube", "v3", credentials=creds)

    queued = list_queued_files(drive)
    mp4_files = [f for f in queued if f["name"].lower().endswith(".mp4")]
    json_by_stem = {
        os.path.splitext(f["name"])[0].lower(): f
        for f in queued
        if f["name"].lower().endswith(".json")
    }

    if not mp4_files:
        print("No queued .mp4 videos found in Google Drive Queue folder.")
        return

    # Files tagged with a youtube_id were already uploaded but never moved (earlier run crashed mid-move).
    for vf in [f for f in mp4_files if (f.get("appProperties") or {}).get("youtube_id")]:
        stem = os.path.splitext(vf["name"])[0]
        print(f"{vf['name']} already uploaded as {vf['appProperties']['youtube_id']}; moving to Published.")
        move_to_published(drive, vf["id"], vf.get("parents", []))
        json_file = json_by_stem.get(stem.lower())
        if json_file:
            move_to_published(drive, json_file["id"], json_file.get("parents", []))
    mp4_files = [f for f in mp4_files if not (f.get("appProperties") or {}).get("youtube_id")]
    if not mp4_files:
        print("No new .mp4 videos left in the Queue folder.")
        return

    for vf in mp4_files[:MAX_UPLOADS_PER_RUN]:
        stem = os.path.splitext(vf["name"])[0]
        json_file = json_by_stem.get(stem.lower())
        meta = load_metadata(drive, json_file, stem)

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            video_path = tmp.name

        try:
            print(f"Processing queued video: {vf['name']}")
            download_file(drive, vf["id"], video_path)
            video_id = upload_to_youtube(youtube, video_path, meta)
            print(f"SUCCESS: Published https://youtube.com/shorts/{video_id}")
            mark_uploaded(drive, vf["id"], video_id)

            move_to_published(drive, vf["id"], vf.get("parents", []))
            if json_file:
                move_to_published(drive, json_file["id"], json_file.get("parents", []))
            print(f"Moved {vf['name']} to Published folder.")
        finally:
            if os.path.exists(video_path):
                os.remove(video_path)


if __name__ == "__main__":
    try:
        main()
    except KeyError as e:
        print(f"Missing required environment variable: {e}", file=sys.stderr)
        sys.exit(1)
