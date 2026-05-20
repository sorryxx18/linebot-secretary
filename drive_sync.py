"""Google Drive sync — downloads files from a shared folder using Service Account."""
from __future__ import annotations

import io
import json
import logging
import os
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

logger = logging.getLogger(__name__)

SA_KEY_PATH = Path(os.getenv("GOOGLE_SA_KEY", "/app/credentials/service-account.json"))
FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "")
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
MANIFEST_PATH = Path(os.getenv("DRIVE_MANIFEST_PATH", "/app/data/drive_manifest.json"))

SUPPORTED_MIMES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.ms-excel.sheet.macroenabled.12": ".xlsm",
    "application/vnd.oasis.opendocument.spreadsheet": ".ods",
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/csv": ".csv",
    "application/vnd.google-apps.document": ".docx",       # Google Doc → export as docx
    "application/vnd.google-apps.spreadsheet": ".xlsx",    # Google Sheet → export as xlsx
}

GOOGLE_EXPORT_MIMES = {
    "application/vnd.google-apps.document": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.google-apps.spreadsheet": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _build_service():
    if not SA_KEY_PATH.exists():
        raise FileNotFoundError(f"Google Service Account JSON 不存在：{SA_KEY_PATH}")
    creds = service_account.Credentials.from_service_account_file(
        str(SA_KEY_PATH), scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def list_folder(folder_id: str | None = None) -> list[dict]:
    """List all files in the folder (non-recursive for now)."""
    fid = folder_id or FOLDER_ID
    if not fid:
        raise RuntimeError("DRIVE_FOLDER_ID is required")
    service = _build_service()
    results = []
    page_token = None
    while True:
        resp = service.files().list(
            q=f"'{fid}' in parents and trashed=false",
            fields="nextPageToken, files(id, name, mimeType, modifiedTime, size, webViewLink)",
            pageSize=100,
            pageToken=page_token,
        ).execute()
        results.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return results


def drive_url(file_meta: dict) -> str:
    """Return a stable original Drive URL for citations."""
    return file_meta.get("webViewLink") or f"https://drive.google.com/open?id={file_meta['id']}"


def saved_filename(file_meta: dict) -> str | None:
    """Name used after export/download to data/raw, or None if unsupported."""
    mime = file_meta.get("mimeType", "")
    suffix = SUPPORTED_MIMES.get(mime)
    if not suffix:
        return None
    name = file_meta["name"]
    safe_name = name if name.lower().endswith(suffix) else name + suffix
    return safe_name.replace("/", "_").replace("\\", "_")


def write_manifest(files: list[dict], path: Path = MANIFEST_PATH) -> None:
    """Persist Drive metadata so the bot can cite original cloud links."""
    path.parent.mkdir(parents=True, exist_ok=True)
    items = []
    for f in files:
        local_name = saved_filename(f)
        items.append({
            "id": f.get("id"),
            "name": f.get("name"),
            "mimeType": f.get("mimeType"),
            "modifiedTime": f.get("modifiedTime"),
            "size": f.get("size"),
            "url": drive_url(f),
            "local_name": local_name,
            "extracted_name": f"{local_name}.txt" if local_name else None,
        })
    path.write_text(json.dumps({"folder_id": FOLDER_ID, "files": items}, ensure_ascii=False, indent=2), encoding="utf-8")


def download_file(file_meta: dict, dest_dir: Path) -> Path | None:
    """Download a single Drive file to dest_dir. Returns saved path or None."""
    service = _build_service()
    fid = file_meta["id"]
    name = file_meta["name"]
    mime = file_meta.get("mimeType", "")

    # Determine export mime & suffix
    if mime in GOOGLE_EXPORT_MIMES:
        export_mime = GOOGLE_EXPORT_MIMES[mime]
        suffix = SUPPORTED_MIMES[mime]
        request = service.files().export_media(fileId=fid, mimeType=export_mime)
    elif mime in SUPPORTED_MIMES:
        suffix = SUPPORTED_MIMES[mime]
        request = service.files().get_media(fileId=fid)
    else:
        logger.info("Skipping unsupported mime %s: %s", mime, name)
        return None

    # Sanitize file name
    safe_name = name if name.lower().endswith(suffix) else name + suffix
    safe_name = safe_name.replace("/", "_").replace("\\", "_")
    dest = dest_dir / safe_name

    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    dest.write_bytes(buf.getvalue())
    logger.info("Downloaded: %s → %s", name, dest)
    return dest


def sync_folder(dest_dir: Path, folder_id: str | None = None) -> dict:
    """Download all supported files from Drive folder to dest_dir."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    files = list_folder(folder_id)
    write_manifest(files)
    downloaded = []
    skipped = []
    errors = []

    for f in files:
        try:
            path = download_file(f, dest_dir)
            if path:
                downloaded.append(f["name"])
            else:
                skipped.append(f["name"])
        except Exception as e:
            logger.error("Failed to download %s: %s", f["name"], e)
            errors.append(f"{f['name']}: {e}")

    return {
        "total": len(files),
        "downloaded": len(downloaded),
        "skipped": len(skipped),
        "errors": errors,
        "files": downloaded,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from rag import RAW_DIR
    print("開始同步 Drive 資料夾...")
    result = sync_folder(RAW_DIR)
    print(f"完成：下載 {result['downloaded']} 個，略過 {result['skipped']} 個")
    if result["errors"]:
        print("錯誤：")
        for e in result["errors"]:
            print(" -", e)
