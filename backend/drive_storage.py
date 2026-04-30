"""Google Drive storage operations (BYOS feature, v7.0).

Wrapper รอบ google-api-python-client สำหรับ CRUD operations ใน Drive ของ user:
upload, download, list, delete, create_folder, ensure_folder, get_metadata.

หน้าที่:
  - แปลง refresh_token (encrypted ใน DB) → live access_token (auto-refresh)
  - ส่งคำสั่ง Drive API ผ่าน HTTPS
  - แยก plain files (PDF, DOCX, TXT) ออกจาก Google Docs native (.gdoc/.gsheet)
    → ใช้ get_media() สำหรับ plain, export() สำหรับ native
  - Resumable upload สำหรับไฟล์ >5MB

ทำไมแยก module นี้ออกจาก drive_oauth.py?
  - oauth.py = "ได้สิทธิ์ยังไง" (one-time flow per user)
  - storage.py = "ใช้สิทธิ์ทำอะไรบ้าง" (per-request CRUD)
  → testable แยกกัน + responsibility ชัด

Mock testing:
  ใช้ googleapiclient.http.HttpMock สำหรับ unit test (ดู scripts/byos_storage_smoke.py)
  → CRUD logic test ได้โดยไม่ต้องชน Drive API จริง
"""
from __future__ import annotations

import io
import json
import logging
from typing import Any, Optional

from .drive_layout import (
    DRIVE_ROOT_FOLDER_NAME,
    MIME_FOLDER,
    MIME_JSON,
    is_google_native,
)
from .drive_oauth import build_credentials_from_refresh_token

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# DriveClient — main wrapper class
# ═══════════════════════════════════════════════════════════════
class DriveClient:
    """Authed Drive API client สำหรับ user คนเดียว.

    Usage:
        client = DriveClient(refresh_token_plaintext)
        folder_id = client.ensure_folder("Personal Data Bank")
        file_id = client.upload_file(folder_id, "report.pdf", data, "application/pdf")
        bytes = client.download_file(file_id)

    Lifetime:
        Access token cached internally โดย google.oauth2.credentials โหมด auto-refresh
        Recommended: สร้าง instance per request (อย่า reuse ข้าม users)
    """

    def __init__(self, refresh_token_plaintext: str):
        """Build authed Drive service.

        Args:
            refresh_token_plaintext: refresh_token หลัง decrypt จาก DB
                (ห้ามส่ง encrypted form มา — caller ควร decrypt ก่อน)
        """
        # Lazy import google API libs (optional dep ของ BYOS feature)
        from googleapiclient.discovery import build

        self._creds = build_credentials_from_refresh_token(refresh_token_plaintext)
        # cache_discovery=False → ไม่ cache schema ลง disk (ปลอดภัยกว่าใน multi-tenant)
        self._service = build("drive", "v3", credentials=self._creds, cache_discovery=False)

    # ───────────────────────────────────────────────────────────
    # Test helper — caller สามารถ inject mock service สำหรับ unit test
    # ───────────────────────────────────────────────────────────
    @classmethod
    def _from_service(cls, service: Any) -> "DriveClient":
        """Bypass OAuth — สร้าง instance จาก service object ที่ pre-built (mock).

        ใช้เฉพาะใน tests. Production code ใช้ __init__ ปกติ.
        """
        instance = cls.__new__(cls)
        instance._creds = None  # type: ignore[assignment]
        instance._service = service
        return instance

    # ═══════════════════════════════════════════════════════════
    # Folder operations
    # ═══════════════════════════════════════════════════════════
    def ensure_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        """หาหรือสร้าง folder ใน Drive — return folder ID.

        ทำ idempotent — ถ้า folder ชื่อนี้มีอยู่แล้ว (ภายใต้ parent ที่ระบุ + ไม่ trash)
        → return ID เดิม. ถ้าไม่มี → สร้างใหม่ + return ID ใหม่.

        Note: drive.file scope จะเห็นเฉพาะ folder ที่ app เคยสร้าง — ดังนั้น
        "ensure" รอบแรกของ user ใหม่จะไปสร้างใหม่เสมอ (แม้ user มี folder ชื่อ
        เดียวกันใน Drive อยู่แล้วจาก app อื่น — เราเห็นไม่ได้)
        """
        query_parts = [
            f"name='{_escape(name)}'",
            f"mimeType='{MIME_FOLDER}'",
            "trashed=false",
        ]
        if parent_id:
            query_parts.append(f"'{parent_id}' in parents")
        else:
            query_parts.append("'root' in parents")

        result = self._service.files().list(
            q=" and ".join(query_parts),
            fields="files(id, name)",
            spaces="drive",
            pageSize=1,
        ).execute()

        if result.get("files"):
            return result["files"][0]["id"]

        body: dict[str, Any] = {"name": name, "mimeType": MIME_FOLDER}
        if parent_id:
            body["parents"] = [parent_id]
        created = self._service.files().create(body=body, fields="id").execute()
        return created["id"]

    def create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        """สร้าง folder ใหม่แม้จะมีชื่อเดียวกันอยู่แล้ว (allow duplicate).

        ส่วนใหญ่ใช้ ensure_folder() แทน. เปิดให้เผื่อ edge case เช่น sub-folder
        ที่ตั้งใจให้ duplicate ได้.
        """
        body: dict[str, Any] = {"name": name, "mimeType": MIME_FOLDER}
        if parent_id:
            body["parents"] = [parent_id]
        created = self._service.files().create(body=body, fields="id").execute()
        return created["id"]

    # ═══════════════════════════════════════════════════════════
    # File CRUD
    # ═══════════════════════════════════════════════════════════
    def upload_file(
        self,
        parent_id: str,
        name: str,
        content: bytes | str,
        mime_type: str,
        resumable: bool | None = None,
    ) -> str:
        """Upload ไฟล์เข้า folder — return Drive file ID.

        Args:
            parent_id: folder ID ที่จะใส่ไฟล์
            name: ชื่อไฟล์ใน Drive
            content: bytes หรือ str (str จะ encode UTF-8 อัตโนมัติ)
            mime_type: MIME type ของไฟล์ (เช่น "application/pdf", "application/json")
            resumable: True = ใช้ resumable upload (แนะนำสำหรับไฟล์ >5MB)
                       None = auto (resumable ถ้า size >5MB)

        Returns:
            Drive file ID (string)
        """
        from googleapiclient.http import MediaIoBaseUpload

        if isinstance(content, str):
            content = content.encode("utf-8")

        if resumable is None:
            resumable = len(content) > 5 * 1024 * 1024  # 5MB threshold

        media = MediaIoBaseUpload(
            io.BytesIO(content),
            mimetype=mime_type,
            resumable=resumable,
        )
        body = {"name": name, "parents": [parent_id]}
        result = self._service.files().create(
            body=body,
            media_body=media,
            fields="id",
        ).execute()
        return result["id"]

    def upload_json(self, parent_id: str, name: str, data: dict | list) -> str:
        """Upload dict/list as pretty-printed JSON file (helper)."""
        payload = json.dumps(data, ensure_ascii=False, indent=2)
        return self.upload_file(parent_id, name, payload, MIME_JSON)

    def update_file_content(
        self,
        file_id: str,
        content: bytes | str,
        mime_type: str,
    ) -> None:
        """Replace ไฟล์เดิมด้วย content ใหม่ (in-place — file_id เดิม).

        ใช้สำหรับ profile.json / graph.json ที่ overwrite บ่อย.
        """
        from googleapiclient.http import MediaIoBaseUpload

        if isinstance(content, str):
            content = content.encode("utf-8")
        media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type, resumable=False)
        self._service.files().update(fileId=file_id, media_body=media).execute()

    def download_file(self, file_id: str, mime_type_hint: Optional[str] = None) -> bytes:
        """Download ไฟล์จาก Drive — return raw bytes.

        จัดการ Google native types โดยอัตโนมัติ:
          - .gdoc / .gsheet / .gslides → export() เป็น PDF (default) / Excel / Powerpoint
          - .pdf / .docx / .txt etc.  → get_media() ตรงๆ

        Args:
            file_id: Drive file ID
            mime_type_hint: ถ้ารู้ MIME type ของไฟล์ล่วงหน้า (ลด API call) — ไม่บังคับ
        """
        from googleapiclient.http import MediaIoBaseDownload

        if mime_type_hint is None:
            mime_type_hint = self.get_metadata(file_id, fields="mimeType")["mimeType"]

        if is_google_native(mime_type_hint):
            # Google Docs native → export as PDF (caller สามารถ override ผ่าน export_*)
            export_mime = "application/pdf"
            if "spreadsheet" in mime_type_hint:
                export_mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            request = self._service.files().export_media(fileId=file_id, mimeType=export_mime)
        else:
            request = self._service.files().get_media(fileId=file_id)

        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _status, done = downloader.next_chunk()
        return buffer.getvalue()

    def download_text(self, file_id: str) -> str:
        """Download ไฟล์ + decode UTF-8 (helper สำหรับ text/json)."""
        return self.download_file(file_id).decode("utf-8")

    def download_json(self, file_id: str) -> Any:
        """Download JSON file + parse (helper)."""
        return json.loads(self.download_text(file_id))

    def delete_file(self, file_id: str) -> None:
        """Move file to trash (recoverable in 30 days)."""
        # Drive API "delete" = permanent. ใช้ "trash" ผ่าน update fields="trashed"
        # → user ยังกู้คืนได้ใน 30 วัน
        self._service.files().update(fileId=file_id, body={"trashed": True}).execute()

    def delete_file_permanent(self, file_id: str) -> None:
        """Permanently delete (no recovery — ใช้ระวัง)."""
        self._service.files().delete(fileId=file_id).execute()

    # ═══════════════════════════════════════════════════════════
    # Listing + metadata
    # ═══════════════════════════════════════════════════════════
    def list_folder(
        self,
        folder_id: str,
        page_size: int = 100,
        only_files: bool = False,
    ) -> list[dict[str, Any]]:
        """List ไฟล์ใน folder — return list of {id, name, mimeType, modifiedTime, size}.

        Auto-pagination จนได้ครบทุก row (Drive API page size = 1000 max).

        Args:
            only_files: True = exclude sub-folders, False = รวม folders
        """
        query_parts = [f"'{folder_id}' in parents", "trashed=false"]
        if only_files:
            query_parts.append(f"mimeType!='{MIME_FOLDER}'")

        all_files: list[dict[str, Any]] = []
        page_token: Optional[str] = None
        while True:
            result = self._service.files().list(
                q=" and ".join(query_parts),
                fields="nextPageToken, files(id, name, mimeType, modifiedTime, size, md5Checksum)",
                spaces="drive",
                pageSize=min(page_size, 1000),
                pageToken=page_token,
            ).execute()
            all_files.extend(result.get("files", []))
            page_token = result.get("nextPageToken")
            if not page_token:
                break
        return all_files

    def get_metadata(self, file_id: str, fields: str = "id, name, mimeType, modifiedTime, size") -> dict[str, Any]:
        """Get file metadata — flexible field selection."""
        return self._service.files().get(fileId=file_id, fields=fields).execute()

    def find_file_by_name(
        self,
        name: str,
        parent_id: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """หาไฟล์ตามชื่อใน folder — return first match หรือ None.

        ใช้สำหรับ idempotent operations เช่น "หา profile.json ใน /personal/"
        """
        query_parts = [f"name='{_escape(name)}'", "trashed=false"]
        if parent_id:
            query_parts.append(f"'{parent_id}' in parents")
        result = self._service.files().list(
            q=" and ".join(query_parts),
            fields="files(id, name, mimeType, modifiedTime)",
            spaces="drive",
            pageSize=1,
        ).execute()
        files = result.get("files", [])
        return files[0] if files else None

    # ═══════════════════════════════════════════════════════════
    # PDB-specific helpers (build on top of generic CRUD)
    # ═══════════════════════════════════════════════════════════
    def upsert_json_file(
        self,
        parent_id: str,
        name: str,
        data: dict | list,
    ) -> str:
        """Upsert: ถ้าไฟล์มีอยู่ → update content. ถ้าไม่มี → create ใหม่.

        ใช้สำหรับ profile.json / graph.json / clusters.json — content ที่
        write-heavy (overwrite ทุกครั้ง user แก้)
        """
        existing = self.find_file_by_name(name, parent_id=parent_id)
        if existing:
            self.update_file_content(
                existing["id"],
                json.dumps(data, ensure_ascii=False, indent=2),
                MIME_JSON,
            )
            return existing["id"]
        return self.upload_json(parent_id, name, data)

    def ensure_pdb_folder_structure(self) -> dict[str, str]:
        """สร้าง folder layout ทั้งหมดของ PDB ใน Drive (ครั้งเดียวต่อ user) — return map ของ {sub_folder_name: id}.

        Layout (ดู drive_layout.py SUB_FOLDERS):
            /Personal Data Bank/
              ├── raw/
              ├── extracted/
              ├── summaries/
              ├── personal/
              ├── data/
              ├── _meta/
              └── _backups/

        Idempotent — เรียกซ้ำได้ ไม่สร้าง duplicate folder.

        Returns:
            {"_root": <id>, "raw": <id>, "extracted": <id>, ...}
        """
        from .drive_layout import SUB_FOLDERS

        root_id = self.ensure_folder(DRIVE_ROOT_FOLDER_NAME)
        result = {"_root": root_id}
        for sub in SUB_FOLDERS:
            result[sub] = self.ensure_folder(sub, parent_id=root_id)
        return result


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════
def _escape(s: str) -> str:
    """Escape single quote สำหรับใช้ใน Drive API query strings.

    Drive API ใช้ q= parameter format `name='value'` — ถ้า value มี ' จะ break query.
    Spec: replace `'` → `\\'` ตาม https://developers.google.com/drive/api/guides/search-files
    """
    return s.replace("\\", "\\\\").replace("'", "\\'")
