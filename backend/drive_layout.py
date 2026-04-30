"""Google Drive folder layout — source-of-truth structure สำหรับ BYOS feature (v7.0).

Folder ที่ Personal Data Bank สร้างใน Drive ของ user — เก็บข้อมูลทุกอย่างเป็น
plaintext JSON / markdown / raw files เพื่อให้ user เปิด Drive ดูเองได้
("Open your Drive right now and verify — we hide nothing").

ทำไมไม่ encrypt content?
  - Trust — user ตรวจสอบได้ว่าเรา process อะไรบ้าง
  - Debug — ฟิลด์ใน profile.json เปิดดูเองได้
  - Backup — Drive ของ user คือ backup ของระบบโดยอัตโนมัติ
  - Refresh tokens (server-side) ก็ encrypt อยู่แล้ว ที่ภาพรวมจึงปลอดภัย
"""
from __future__ import annotations

# ═══════════════════════════════════════════════════════════════
# Root folder — ชื่อ folder ที่ user จะเห็นใน Drive
# ═══════════════════════════════════════════════════════════════
# default = "Personal Data Bank" (สอดคล้องกับ rebrand v6.1.0)
# ถ้า user/แดง decide เปลี่ยนเป็น "/PDB/" → แก้ที่นี่จุดเดียว
DRIVE_ROOT_FOLDER_NAME = "Personal Data Bank"

# ═══════════════════════════════════════════════════════════════
# Sub-folders ใน root
# ═══════════════════════════════════════════════════════════════
# raw/         — ไฟล์ต้นฉบับ (PDF, DOCX, TXT, MD ที่ user upload)
# extracted/   — extracted plain text (.txt) ของแต่ละไฟล์ (ใช้สำหรับ embedding)
# summaries/   — AI-generated summaries (.md) ของแต่ละไฟล์
# personal/    — profile.json + contexts.json (personality + identity + memory)
# data/        — clusters.json, graph.json, relations.json, chat_history.json
# _meta/       — version.txt + manifest.json (สำหรับ schema versioning + recovery)
# _backups/    — auto-rotated backup zips (สัปดาห์ละครั้ง)
SUB_FOLDERS: tuple[str, ...] = (
    "raw",
    "extracted",
    "summaries",
    "personal",
    "data",
    "_meta",
    "_backups",
)

# ═══════════════════════════════════════════════════════════════
# Schema version — bump เมื่อเปลี่ยน folder layout
# ═══════════════════════════════════════════════════════════════
# v1.0 = initial layout (v7.0.0 launch)
# ถ้าอนาคตเปลี่ยน schema → bump เลข + เพิ่ม migration ที่อ่าน version เก่าได้
DRIVE_SCHEMA_VERSION = "1.0"

# ═══════════════════════════════════════════════════════════════
# Standard file names ใน sub-folders
# ═══════════════════════════════════════════════════════════════
PROFILE_JSON = "personal/profile.json"
CONTEXTS_JSON = "personal/contexts.json"
CLUSTERS_JSON = "data/clusters.json"
GRAPH_JSON = "data/graph.json"
RELATIONS_JSON = "data/relations.json"
CHAT_HISTORY_JSON = "data/chat_history.json"
META_VERSION_TXT = "_meta/version.txt"
META_MANIFEST_JSON = "_meta/manifest.json"

# ═══════════════════════════════════════════════════════════════
# Path helpers
# ═══════════════════════════════════════════════════════════════
def raw_path_for(file_id: str, original_name: str) -> str:
    """Path ของไฟล์ต้นฉบับใน Drive: raw/{file_id}_{original_name}.

    ทำไมต้องใส่ file_id? — กัน collision ถ้า user upload 2 ไฟล์ชื่อเดียวกัน
    + ทำให้ผู้กรองรู้ทันทีว่า row ไหนใน DB คู่กับไฟล์ไหนใน Drive.
    """
    return f"raw/{file_id}_{original_name}"


def extracted_path_for(file_id: str) -> str:
    """Path ของ extracted text: extracted/{file_id}.txt"""
    return f"extracted/{file_id}.txt"


def summary_path_for(file_id: str) -> str:
    """Path ของ AI summary: summaries/{file_id}.md"""
    return f"summaries/{file_id}.md"


def backup_path_for(timestamp_iso: str) -> str:
    """Path ของ weekly backup zip: _backups/{YYYY-MM-DD_HH-mm}.zip"""
    # timestamp_iso จะถูก clean เป็น filename-safe ก่อนส่งมา
    return f"_backups/{timestamp_iso}.zip"


# ═══════════════════════════════════════════════════════════════
# MIME types ที่ Drive ใช้
# ═══════════════════════════════════════════════════════════════
MIME_FOLDER = "application/vnd.google-apps.folder"
MIME_JSON = "application/json"
MIME_TEXT = "text/plain"
MIME_MARKDOWN = "text/markdown"

# Google Docs native types (ต้องใช้ export() แทน get_media() ตอน download)
GOOGLE_NATIVE_TYPES = frozenset({
    "application/vnd.google-apps.document",     # .gdoc
    "application/vnd.google-apps.spreadsheet",  # .gsheet
    "application/vnd.google-apps.presentation", # .gslides
    "application/vnd.google-apps.drawing",      # .gdraw
})


def is_google_native(mime_type: str) -> bool:
    """True ถ้าไฟล์เป็น Google Docs native type (ต้อง export, ใช้ get_media ไม่ได้)."""
    return mime_type in GOOGLE_NATIVE_TYPES


# ═══════════════════════════════════════════════════════════════
# Storage source enum (สำหรับ files.storage_source column)
# ═══════════════════════════════════════════════════════════════
STORAGE_SOURCE_LOCAL = "local"             # managed mode — ไฟล์อยู่ใน Fly.io volume
STORAGE_SOURCE_DRIVE_UPLOADED = "drive_uploaded"  # BYOS — user upload ผ่าน UI → ส่งขึ้น Drive
STORAGE_SOURCE_DRIVE_PICKED = "drive_picked"      # BYOS — user pick ไฟล์เดิมใน Drive ผ่าน Picker

VALID_STORAGE_SOURCES = frozenset({
    STORAGE_SOURCE_LOCAL,
    STORAGE_SOURCE_DRIVE_UPLOADED,
    STORAGE_SOURCE_DRIVE_PICKED,
})


# ═══════════════════════════════════════════════════════════════
# Storage mode enum (สำหรับ users.storage_mode column)
# ═══════════════════════════════════════════════════════════════
STORAGE_MODE_MANAGED = "managed"  # default — เก็บใน server volume
STORAGE_MODE_BYOS = "byos"        # เก็บใน Google Drive ของ user

VALID_STORAGE_MODES = frozenset({STORAGE_MODE_MANAGED, STORAGE_MODE_BYOS})
