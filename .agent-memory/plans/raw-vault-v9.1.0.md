# Plan: Raw File Vault — v9.1.0

**Author:** แดง (Daeng)
**Date:** 2026-05-07
**Status:** plan_pending_approval
**Foundation:** master HEAD `ed22b1b` (v9.0.0 multimodal expansion)
**Estimated effort:** เขียว 4-5 ชม. + ฟ้า 1-2 ชม. = ~6-7 ชม. รวม

---

## 🎯 Goal

ระบบเก็บไฟล์ที่ "ระบบไม่รองรับการประมวลผล" ให้เป็น **กิจจะลักษณะ** — เก็บแบบ official ไม่ใช่ทิ้ง ให้ user มองเห็น จัดการ และดาวน์โหลดได้

### ทำไม
ตอนนี้ — ไฟล์ที่ ext ไม่อยู่ใน `ALL_FILE_TYPES` (เช่น `.zip`, `.doc`, `.pages`, `.dwg`, `.psd`) → backend `/api/upload` ตอบ skip + UNSUPPORTED_TYPE → **ไฟล์หายไปทันที**

ปัญหา:
1. User เสียเวลา + bandwidth upload → ระบบทิ้ง
2. ไม่มี record ว่าเคยพยายาม
3. Future: เมื่อเรา add support → ไม่มีไฟล์ให้ reprocess
4. Vault use case (เก็บไฟล์สำคัญที่ AI อ่านไม่ได้ — เช่น `.psd` portfolio, `.zip` archive) ทำไม่ได้

### หลังทำเสร็จ
- Upload ไฟล์ **อะไรก็ได้** (ภายใน size + count limit) → save raw + mark "vault_only"
- UI มี section แยก "📦 ไฟล์ที่ AI อ่านไม่ได้" — แสดงไฟล์ raw_only
- User ทำได้: download / delete / view metadata / **"ลองอีกครั้งด้วย AI"** (เผื่อมี GOOGLE_API_KEY แล้ว)
- ไม่ join organize/cluster/chat (vault อยู่แยก)
- Future: เมื่อเพิ่ม format support → background job scan vault + auto-reprocess

---

## 📚 Context

### Stack ที่กระทบ
- Backend: `main.py` (`/api/upload`, `/api/files`, delete/share/reprocess)
- Backend: `database.py` (File model + new column?)
- Backend: `extraction.py` (ใช้เดิม — vault skip extract)
- Backend: `plan_limits.py` (vault counts toward quota?)
- Backend: `storage_router.py` (push raw → Drive ไม่เปลี่ยน)
- Backend: `organizer.py` (filter out vault จาก clustering)
- Backend: `vector_search.py` (vault NOT indexed)
- Frontend: `app.html` (new section / tab in My Data)
- Frontend: `app.js` (new render function + filter)

### Decisions ก่อนหน้าที่เกี่ยวข้อง
- **v7.5.0:** structured skip schema `{code, message, suggestion}` — เราเปลี่ยนจาก SKIP เป็น "vault_only" สำหรับ UNSUPPORTED_TYPE เท่านั้น (ที่อื่นยัง skip ปกติ)
- **v8.0.x:** plan_limits production values (Free 50/500MB) — vault ใช้ quota เดียวกัน
- **v9.0.0 Phase B v2:** ai_ingest module + GOOGLE_API_KEY graceful degradation — vault จะใช้ "Try AI" button ที่ trigger ai_ingest

### What stays the same
- File size limit, count limit, storage limit — vault ใช้เหมือน processed files
- BYOS Drive sync — push raw เหมือนเดิม (folder อาจเปลี่ยน)
- delete cascade — vault file ลบเหมือนปกติ
- skip codes อื่น (FILE_TOO_LARGE, EMPTY_FILE, QUOTA_EXCEEDED) — ยัง skip เหมือนเดิม **ไม่ vault**

---

## 📁 Files to Create / Modify

### Backend
- [ ] `backend/database.py` (modify) — เพิ่ม column `file_kind` + migration
- [ ] `backend/main.py` (modify):
  - upload endpoint: เปลี่ยน UNSUPPORTED_TYPE skip → save raw with file_kind="vault_only"
  - new endpoint `POST /api/files/{file_id}/promote` — ย้าย vault → processed (ลอง extract)
  - `_serialize_file`: expose `file_kind`
  - list endpoint: support `?kind=` filter
  - delete endpoint: handle vault files (cascade ปกติ)
- [ ] `backend/organizer.py` (modify) — filter `file_kind="processed"` ในทุก query
- [ ] `backend/vector_search.py` (modify) — verify vault ไม่ถูก index
- [ ] `backend/plan_limits.py` (no change) — vault ใช้ quota เดียวกัน
- [ ] `backend/storage_router.py` (modify) — Drive folder routing: vault → `vault/`

### Frontend
- [ ] `legacy-frontend/app.html` (modify):
  - เพิ่ม tab/section "📦 Vault (N)" ใน My Data page
  - หรือใช้ filter chip "ทั้งหมด / ประมวลผลแล้ว / Vault"
  - Vault file card: download + delete + "ลองวิเคราะห์อีกครั้ง" button
- [ ] `legacy-frontend/app.js` (modify):
  - `renderFileList`: เพิ่ม `file_kind` badge ตอน render
  - new `loadVaultFiles()` หรือ filter ในตัวเดิม
  - new `promoteVaultFile(id)` handler
  - i18n keys: `vault.title`, `vault.description`, `vault.tryAgain`, `vault.download`, etc.
- [ ] `legacy-frontend/styles.css` (modify) — `.vault-section`, `.file-vault-badge`, `.btn-promote` styles

### Tests (สำหรับฟ้า)
- [ ] `tests/test_raw_vault_v910.py` (create) — pytest unit
- [ ] `scripts/raw_vault_e2e_verify.py` (create) — backend E2E TestClient
- [ ] `tests/e2e-ui/v9.1.0-vault.spec.js` (create) — Playwright real browser

### Documentation
- [ ] `README.md` (modify) — update features section + version history
- [ ] `.agent-memory/plans/raw-vault-v9.1.0.md` (this file) — archive after done

---

## 📡 API Changes

### A. `POST /api/upload` (modify behavior)

**Before (v9.0.0):**
```python
if ext not in allowed_types:
    skipped.append(_make_skip("UNSUPPORTED_TYPE", ...))
    continue  # ไฟล์ถูกทิ้ง
```

**After (v9.1.0):**
```python
if ext not in allowed_types:
    # Save as vault — store raw, no extract, no index
    file_id = gen_id()
    raw_path = save_raw_to_disk(...)
    INSERT files(
        ..., file_kind="vault_only", extracted_text="",
        extraction_status="vault", processing_status="vault_only"
    )
    uploaded.append({...with file_kind="vault_only"})
    continue  # ไม่ extract, ไม่ index
```

**Response 200 (extended):**
```json
{
  "uploaded": [
    {"id": "abc", "filename": "ok.pdf", "filetype": "pdf",
     "file_kind": "processed", "text_length": 5432},
    {"id": "def", "filename": "design.psd", "filetype": "psd",
     "file_kind": "vault_only", "text_length": 0,
     "vault_reason": "format not supported by AI extraction"}
  ],
  "count": 2,
  "skipped": [
    {"filename": "huge.zip", "code": "FILE_TOO_LARGE", ...}
  ]
}
```

**Skip codes ที่ยัง SKIP (ไม่ vault):**
- `FILE_TOO_LARGE` — ไฟล์ใหญ่เกิน plan limit
- `EMPTY_FILE` — 0 bytes
- `QUOTA_EXCEEDED` — เกินจำนวนไฟล์ ทั้ง vault + processed รวมกัน

**Skip code ใหม่:**
- `UNSUPPORTED_TYPE` — **ลบ** code นี้ (ไฟล์เข้า vault แทน)

### B. `GET /api/files?kind={all|processed|vault}` (modify with filter)

**Query params (new):**
- `kind=all` (default) — ทุกไฟล์
- `kind=processed` — เฉพาะ file_kind="processed"
- `kind=vault` — เฉพาะ file_kind="vault_only"

**Response 200 (file object extended):**
```json
{
  "files": [{
    "id": "...", "filename": "...", "filetype": "psd",
    "file_kind": "vault_only",       // ใหม่
    "vault_reason": "format not supported",  // เผื่ออธิบาย
    "extraction_status": "vault",     // ใหม่ status
    "text_length": 0,
    "uploaded_at": "...",
    "is_locked": false,
    ...
  }]
}
```

### C. `POST /api/files/{file_id}/promote` (new)

**Purpose:** User กด "ลองวิเคราะห์อีกครั้ง" บน vault file → backend ลอง extract + AI ingest

**Request:**
```http
POST /api/files/{file_id}/promote
Authorization: Bearer <JWT>
```

**Process:**
```
1. Get file, verify user_id == current_user.id
2. ถ้า file_kind != "vault_only" → 400 NOT_VAULT
3. ถ้า raw_path missing → 404 RAW_MISSING
4. ลอง extract_text(raw_path, ext)
5. ถ้า marker [AI ingest needed:] → call ai_ingest.ingest_via_ai()
6. อัพเดท: file.extracted_text, file.file_kind="processed",
           file.extraction_status, file.processing_status="uploaded"
7. ถ้ายัง marker [Unsupported / AI not configured / etc.] → file_kind ยังเป็น "vault_only", ตอบ marker
```

**Response 200 (success):**
```json
{
  "status": "ok",
  "file_id": "...",
  "promoted": true,
  "file_kind": "processed",
  "text_length": 1234,
  "extraction_status": "ok"
}
```

**Response 200 (still vault):**
```json
{
  "status": "ok",
  "file_id": "...",
  "promoted": false,
  "file_kind": "vault_only",
  "extraction_status": "unsupported",
  "message": "Still no extraction available — file remains in vault"
}
```

**Errors:**
- `400 NOT_VAULT` — file_kind != "vault_only"
- `404 FILE_NOT_FOUND` — file ไม่มี / ไม่ใช่ของ user
- `404 RAW_MISSING` — raw_path file หาย
- `403 LOCKED` — file is_locked=True

### D. `GET /api/files/{file_id}/download` (no API change, but vault must work)

ตรวจให้ download endpoint ทำงานปกติกับ file_kind="vault_only"

### E. `DELETE /api/files/{file_id}` (no API change, vault delete works)

ลบ vault file = ลบเหมือนปกติ + cascade FK + remove raw + Drive trash

### F. `GET /api/stats` (response extended)

เพิ่ม `vault_count` และ `processed_count` ใน response:
```json
{
  "total_files": 50,
  "processed_files": 35,    // file_kind="processed"
  "vault_files": 15,        // file_kind="vault_only"  ← ใหม่
  "ready_files": 30,
  ...
}
```

---

## 💾 Data Model Changes

### `files` table — เพิ่ม column

```python
class File(Base):
    # ... existing columns ...

    # v9.1.0 — Raw File Vault
    file_kind = Column(String, default="processed", index=True)
    # values: "processed" | "vault_only"
    #
    # "processed" = ไฟล์ที่ extract ได้ (รวม partial/error markers)
    #               → join organize, cluster, chat, vector index
    # "vault_only" = ไฟล์ที่เก็บ raw แต่ AI ยังอ่านไม่ได้ (ext ไม่อยู่ใน ALL_FILE_TYPES)
    #               → แค่ download ได้, ไม่ join AI pipeline
    #
    # Indexed เพราะ filter list ใช้บ่อย
```

### Migration (idempotent — ทำใน database.py init_db())

```python
# v9.1.0 Migration — Raw Vault file_kind column
cursor = await db.execute("PRAGMA table_info(files)")
file_cols_v910 = [row[1] for row in await cursor.fetchall()]
if "file_kind" not in file_cols_v910:
    await db.execute(
        "ALTER TABLE files ADD COLUMN file_kind TEXT DEFAULT 'processed'"
    )
    migrated = True
    print("  → Added: files.file_kind (v9.1.0 — Raw Vault)")

# Index
try:
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_files_file_kind ON files(file_kind)"
    )
except Exception as e:
    print(f"  ⚠️ files.file_kind index warning: {e}")
```

**Backfill:** existing files default `file_kind="processed"` (column default) — no auto-update needed because all existing rows had ext in allowed_types (ถ้าไม่ใช่ก็ไม่ได้ถูก save อยู่แล้ว)

### `extraction_status` extended values

เพิ่ม value ใหม่:
- `"vault"` — สำหรับ file_kind="vault_only" (ก่อนหน้า: ok, empty, encrypted, ocr_failed, unsupported, partial)

### `processing_status` extended values

เพิ่ม value ใหม่:
- `"vault_only"` — สำหรับ file_kind="vault_only" (ก่อนหน้า: uploaded, processing, organized, ready, error, reprocessed)

---

## 🔧 Step-by-Step Implementation (สำหรับเขียว)

### Step 1: Database migration + File model
```python
# backend/database.py
# 1.1 เพิ่ม column ใน File class:
file_kind = Column(String, default="processed", index=True)

# 1.2 เพิ่ม migration ใน init_db() (ตามแบบ extraction_status/chunk_count migration ของ v7.5.0)
```

**Verify:**
- รัน `python -c "from backend.database import init_db; import asyncio; asyncio.run(init_db())"`
- ดู log "Added: files.file_kind"
- รันซ้ำ → ดู "Schema up to date" (idempotent)

### Step 2: Update upload endpoint (`backend/main.py`)

แทนที่ block:
```python
if ext not in allowed_types:
    skipped.append(_make_skip("UNSUPPORTED_TYPE", original_name, ext=ext or "unknown"))
    continue
```

ด้วย:
```python
# v9.1.0 — Raw Vault: ext ที่ระบบไม่รองรับ → save raw แต่ไม่ extract/index
is_vault = ext not in allowed_types

# Skip flow ที่เหลือ (size/quota/empty) ตรวจปกติ
# ... existing checks for quota, size, empty file ...

# Save raw to disk
# ... existing logic ...

if is_vault:
    # Vault file: skip extract + ai_ingest, set file_kind
    extracted = ""
    content_hash = None  # ไม่ index สำหรับ vault
    ext_status = "vault"
    proc_status = "vault_only"
    file_kind = "vault_only"
else:
    extracted = extract_text(raw_path, ext)
    if extracted.startswith("[AI ingest needed:"):
        # ... existing AI ingest dispatch ...
    content_hash = compute_content_hash(extracted)
    ext_status = classify_extraction_status(extracted)
    proc_status = "uploaded"
    file_kind = "processed"

db_file = File(
    id=file_id, user_id=current_user.id,
    filename=original_name, filetype=ext,
    raw_path=raw_path, extracted_text=extracted,
    processing_status=proc_status,
    content_hash=content_hash,
    extraction_status=ext_status,
    file_kind=file_kind,  # v9.1.0
)
```

**Verify:**
- Upload `.zip` → ตอบ count=1 + uploaded[0].file_kind="vault_only"
- Upload `.pdf` → ตอบ count=1 + uploaded[0].file_kind="processed"
- Upload .zip 200MB → SKIPPED FILE_TOO_LARGE (ยังไม่ vault — ตรวจ size ก่อน)
- Upload .zip 0 bytes → SKIPPED EMPTY_FILE (ยังไม่ vault — ตรวจ empty ก่อน)
- Upload เกิน file_limit → SKIPPED QUOTA_EXCEEDED

### Step 3: `_serialize_file` expose new fields

```python
def _serialize_file(f: File) -> dict:
    return {
        # ... existing fields ...
        "file_kind": getattr(f, "file_kind", "processed") or "processed",
        "vault_reason": (
            "format not supported by AI extraction"
            if getattr(f, "file_kind", "") == "vault_only"
            else None
        ),
    }
```

### Step 4: List endpoint filter

```python
@app.get("/api/files")
async def list_files(
    kind: str = Query("all", regex="^(all|processed|vault)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(File).where(File.user_id == current_user.id)
    if kind == "processed":
        query = query.where(File.file_kind == "processed")
    elif kind == "vault":
        query = query.where(File.file_kind == "vault_only")
    query = query.options(selectinload(File.insight), selectinload(File.summary)).order_by(File.uploaded_at.desc())
    result = await db.execute(query)
    files = result.scalars().all()
    return {"files": [_serialize_file(f) for f in files]}
```

### Step 5: Promote endpoint

```python
@app.post("/api/files/{file_id}/promote")
async def promote_vault_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """ลอง extract + AI ingest ไฟล์ vault เพื่อย้ายเป็น processed (v9.1.0)."""
    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == current_user.id)
    )
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail={"error": {"code": "FILE_NOT_FOUND"}})
    if getattr(file, "is_locked", False):
        raise HTTPException(status_code=403, detail={"error": {"code": "LOCKED"}})
    if file.file_kind != "vault_only":
        raise HTTPException(status_code=400, detail={"error": {"code": "NOT_VAULT"}})
    if not file.raw_path or not os.path.exists(file.raw_path):
        raise HTTPException(status_code=404, detail={"error": {"code": "RAW_MISSING"}})

    # Re-check ext now (อาจ allowed_types ขยายแล้ว)
    from .plan_limits import get_limits as _gl
    limits = _gl(current_user)
    if file.filetype not in limits["allowed_file_types"]:
        return {
            "status": "ok",
            "file_id": file_id,
            "promoted": False,
            "file_kind": "vault_only",
            "extraction_status": "vault",
            "message": "ไฟล์ยังไม่รองรับ — เก็บใน vault ต่อไป",
        }

    # Try extract
    extracted = extract_text(file.raw_path, file.filetype)
    if extracted.startswith("[AI ingest needed:"):
        try:
            from .ai_ingest import ingest_via_ai
            extracted = await ingest_via_ai(file.raw_path, file.filetype)
        except Exception as e:
            extracted = f"[AI ingest error: {type(e).__name__}: {str(e)[:200]}]"

    file.extracted_text = extracted
    file.content_hash = compute_content_hash(extracted)
    file.extraction_status = classify_extraction_status(extracted)
    file.file_kind = "processed"
    file.processing_status = "uploaded"  # ต้อง organize ใหม่
    await db.commit()

    return {
        "status": "ok",
        "file_id": file_id,
        "promoted": True,
        "file_kind": "processed",
        "text_length": len(extracted),
        "extraction_status": file.extraction_status,
    }
```

### Step 6: Stats endpoint

ใน `GET /api/stats` เพิ่ม count:
```python
processed_count = sum(1 for f in files if f.file_kind == "processed")
vault_count = sum(1 for f in files if f.file_kind == "vault_only")
return {
    # ... existing ...
    "processed_files": processed_count,
    "vault_files": vault_count,
}
```

### Step 7: Filter vault ออกจาก organize/cluster/chat

`backend/organizer.py:21` และ `:433`:
```python
# Before
select(File).where(File.user_id == user_id, File.extracted_text != "")

# After (v9.1.0)
select(File).where(
    File.user_id == user_id,
    File.extracted_text != "",
    File.file_kind == "processed",  # exclude vault
)
```

### Step 8: BYOS Drive routing (`backend/storage_router.py`)

ถ้า BYOS — push raw ไป folder แยก:
```python
# ใน push_raw_file_to_drive_if_byos:
if file_kind == "vault_only":
    drive_folder = "vault"  # → My Drive/Personal Data Bank/vault/
else:
    drive_folder = "raw"
```

### Step 9: Frontend — render + UI

#### app.html
เพิ่ม filter chips/tabs ก่อน file-list:
```html
<div class="file-filter-chips">
  <button class="chip active" data-kind="all">ทั้งหมด <span id="count-all">0</span></button>
  <button class="chip" data-kind="processed">ประมวลผลแล้ว <span id="count-processed">0</span></button>
  <button class="chip" data-kind="vault">📦 Vault <span id="count-vault">0</span></button>
</div>
```

#### app.js
- Add `loadFiles()` รับ kind param
- Filter chips click → reload with kind
- `renderFileList`: เพิ่ม badge "📦 Vault" ถ้า file_kind="vault_only"
- เพิ่มปุ่ม "ลองวิเคราะห์อีกครั้ง" (promote button) บน vault card
- `promoteVaultFile(id)` handler → POST `/api/files/{id}/promote`
- i18n keys (TH + EN):
  - `vault.title`, `vault.description`
  - `vault.badge` = "Vault" / "เก็บในคลัง"
  - `vault.tryAgain` = "ลองวิเคราะห์อีกครั้ง" / "Try analyze again"
  - `vault.promoteSuccess` / `vault.promoteFail` toasts
  - `myData.filterAll`, `filterProcessed`, `filterVault`

#### styles.css
```css
.file-vault-badge {
  background: #e9d5ff; color: #6b21a8;
  font-weight: 500; padding: 2px 8px; border-radius: 12px;
  font-size: 11px;
}
.file-filter-chips { display: flex; gap: 8px; margin-bottom: 16px; }
.file-filter-chips .chip { ... }
.file-filter-chips .chip.active { background: #6366f1; color: #fff; }
.btn-promote { background: #ede9fe; color: #5b21b6; ... }
```

---

## 🧪 Test Scenarios (สำหรับฟ้า)

### Layer 1: pytest unit (`tests/test_raw_vault_v910.py`)

#### Migration
- `test_migration_adds_file_kind_column`
- `test_migration_idempotent` (รันซ้ำ no error)
- `test_existing_files_default_to_processed` (backfill)

#### File model
- `test_new_file_default_file_kind_processed`
- `test_serialize_file_exposes_file_kind_and_vault_reason`

#### Upload behavior
- `test_upload_unsupported_ext_creates_vault_record`
- `test_upload_supported_ext_creates_processed_record`
- `test_upload_too_large_unsupported_still_skipped` (FILE_TOO_LARGE wins)
- `test_upload_empty_unsupported_still_skipped` (EMPTY_FILE wins)
- `test_upload_quota_full_blocks_both_kinds` (quota counts both)
- `test_vault_file_has_no_extracted_text` (empty string)
- `test_vault_file_has_no_content_hash` (None — no semantic search)

#### List endpoint filter
- `test_list_files_default_returns_all_kinds`
- `test_list_files_kind_processed_excludes_vault`
- `test_list_files_kind_vault_excludes_processed`
- `test_list_files_invalid_kind_param_returns_422`

#### Promote endpoint
- `test_promote_vault_to_processed_success` (after format added)
- `test_promote_already_processed_returns_400_NOT_VAULT`
- `test_promote_missing_file_returns_404`
- `test_promote_cross_user_returns_404` (security)
- `test_promote_locked_file_returns_403`
- `test_promote_raw_missing_returns_404_RAW_MISSING`
- `test_promote_still_unsupported_keeps_vault_kind`

#### Organize/cluster excludes vault
- `test_organize_skips_vault_files`
- `test_clusters_endpoint_excludes_vault_files`
- `test_chat_does_not_use_vault_files_in_rag` (mock vector_search)

### Layer 2: Backend E2E TestClient (`scripts/raw_vault_e2e_verify.py`)

```
SECTION A — Vault Upload Behavior (8 cases)
  A.1 Upload .zip → vault_only kind in response
  A.2 Upload .doc → vault_only kind
  A.3 Upload .heic → processed (already supported)
  A.4 Upload mixed batch (pdf + zip) → 2 uploaded, 0 skipped, kinds correct
  A.5 vault count toward file_limit (free=50)
  A.6 vault count toward storage_limit_mb
  A.7 .zip 200MB+ → SKIPPED FILE_TOO_LARGE (not vault)
  A.8 0-byte .zip → SKIPPED EMPTY_FILE (not vault)

SECTION B — List Filter (6 cases)
  B.1 GET /api/files default = all kinds
  B.2 ?kind=processed excludes vault
  B.3 ?kind=vault excludes processed
  B.4 ?kind=invalid → 422
  B.5 Each file has file_kind in response
  B.6 vault files have vault_reason populated

SECTION C — Promote Endpoint (8 cases)
  C.1 POST promote on vault file → file_kind="processed"
  C.2 promote on already-processed → 400 NOT_VAULT
  C.3 promote on missing file → 404
  C.4 promote cross-user → 404 (no info leak)
  C.5 promote on locked file → 403
  C.6 promote unsupported still vault → promoted=false response
  C.7 promote re-extracts via Tesseract OCR (image case)
  C.8 promote re-extracts via AI (audio case if GOOGLE_API_KEY set)

SECTION D — Vault excluded from AI pipeline (4 cases)
  D.1 organize-new ignores vault files
  D.2 clusters response doesn't include vault
  D.3 vector_search doesn't index vault
  D.4 chat sources never reference vault files

SECTION E — Stats + BYOS (3 cases)
  E.1 /api/stats returns vault_files + processed_files counts
  E.2 BYOS push: vault file → vault/ folder (mocked)
  E.3 Existing files have file_kind="processed" after migration
```

### Layer 3: Playwright real browser (`tests/e2e-ui/v9.1.0-vault.spec.js`)

```
- Filter chips render correctly
- Click "Vault" chip → only vault files shown
- vault file card shows 📦 badge
- Click "ลองวิเคราะห์อีกครั้ง" → POST /promote called
- Successful promote → file moves out of vault list
- Mobile viewport: chips wrap, buttons accessible
- Empty vault state: "ยังไม่มีไฟล์ใน vault"
```

### Layer 4: Manual smoke (เปิด browser จริง)

- [ ] Drag .zip + .pdf together → ดูทั้งใน list
- [ ] Switch tab Vault ↔ Processed → render ถูก
- [ ] กด Try Again บน vault → ดู behavior (ยัง vault ถ้าไม่ support)
- [ ] เปิด Drive ดู folder vault/ มีไฟล์
- [ ] iPhone Safari upload .pages → ขึ้น vault
- [ ] Console: ไม่มี red errors

---

## ✅ Done Criteria

- [ ] Migration เพิ่ม column file_kind สำเร็จ + idempotent
- [ ] Upload .zip / .doc / .pages / etc. → save vault (ไม่ทิ้ง)
- [ ] file_kind="vault_only" อยู่ใน DB + serialize ถูก
- [ ] List filter `?kind=` ทำงานทั้ง 3 ค่า
- [ ] Promote endpoint ทำงาน + handle 5 error cases
- [ ] Organize/cluster/chat **ไม่ใช้** vault files (verified)
- [ ] Stats endpoint แสดง vault_files + processed_files
- [ ] Frontend filter chips + vault badge + try-again button
- [ ] BYOS push vault → folder แยก (or same folder with metadata)
- [ ] Tests pass: ~30 pytest + ~30 backend E2E + ~7 Playwright + 238 regression
- [ ] Performance: vault upload เร็วกว่า processed (no extract)

---

## ⚠️ Risks / Open Questions

### Risks
1. **Quota fill rate** — vault uploads ใช้ disk เร็ว เพราะ user อาจ upload .zip หลาย GB
   - **Mitigation:** ตอนนี้ Free 500MB / Starter 5GB — vault counts toward — user เห็นเอง
2. **Drive folder pollution** — vault files mix กับ raw processed → user งงใน Drive
   - **Mitigation:** แยก folder `vault/` ใน BYOS layout
3. **Existing user expects UNSUPPORTED rejection** — เปลี่ยน behavior อาจสับสน
   - **Mitigation:** Toast: "ไฟล์เก็บใน Vault — AI ยังอ่านไม่ได้ แต่เก็บไว้ให้แล้ว"
4. **Reprocess after format added** — vault files ไม่ auto-promote เมื่อเรา add support
   - **Mitigation:** Phase 2: background scan job (defer)
5. **MIME spoofing** — user เปลี่ยน .exe เป็น .pdf — ปกติ extract fail → marker error → file_kind="processed" with broken text
   - **Mitigation:** ทำเหมือนเดิม (ext-based check) — ไม่ verify magic bytes

### Open Questions ให้ user ตัดสิน
- **Q1:** Vault ใช้ quota เดียวกันกับ processed หรือแยก?
  - 🟢 แดงแนะนำ: **เดียวกัน** (simpler + เห็น storage cost รวม)
  - 🟡 alternative: vault quota แยก (vault_storage_limit_mb=200MB)
- **Q2:** UI design — filter chips, tab, หรือ separate page?
  - 🟢 แดงแนะนำ: **filter chips** (compact, ง่าย, ไม่ต้องเพิ่ม route)
  - 🟡 alternative: separate "Vault" page ใน sidebar
- **Q3:** "Try Again" button ทำอะไรเมื่อยังไม่รองรับ?
  - 🟢 แดงแนะนำ: **toast informative** "ไฟล์ยังไม่รองรับ — รอ feature ใหม่"
  - 🟡 alternative: hide button if not promotable (predict ก่อน)
- **Q4:** Auto-promote เมื่อ admin ขยาย allowed_file_types?
  - 🟢 แดงแนะนำ: **manual only ใน v9.1.0** (auto = Phase 2)
- **Q5:** vault file สร้าง search index ไหม?
  - ✅ **USER DECIDED 2026-05-07:** สร้าง — แต่เฉพาะ filename + ext (ไม่ใช่เนื้อหา)
  - AI ต้องค้นเจอได้ว่ามีไฟล์ชื่ออะไรบ้าง + เดาว่าน่าจะเป็นอะไรจาก filename+ext
  - **Implementation:** vault file มี `extracted_text = "[Vault file] {filename_no_ext} (extension: {ext})"` + tokenized filename keywords (split on -_.)
  - ไม่ call LLM (ค่าใช้จ่าย $0)
  - vector_search (TF-IDF) จะ index ข้อความสั้นนี้ → AI chat retrieval หาเจอ
  - AI in chat response รู้ว่าเป็น vault → reply: "พบไฟล์ {name} ในคลัง — AI อ่านเนื้อหาไม่ได้ แต่ดาวน์โหลดได้"
- **Q6:** dedupe สำหรับ vault?
  - 🟢 แดงแนะนำ: **SHA-256 ของ raw bytes** (ใช้ column ใหม่ `raw_hash` หรือใช้ content_hash)
  - 🟡 v9.1.0 defer — vault ไม่ dedupe ก่อน (single-user use case นี้)
- **Q7:** Notification ใน UI ตอนเข้า vault?
  - 🟢 แดงแนะนำ: **toast เดียว** "เก็บใน Vault — ดูที่แท็บ Vault"
- **Q8:** vault file สามารถ share ผ่าน /api/files/{id}/share ได้ไหม?
  - 🟢 แดงแนะนำ: **ได้** (download link ปกติ)

---

## 📌 Notes for นักพัฒนา

### Convention ที่ต้องรักษา
1. **Path traversal defense** — ใช้ `os.path.basename` กับ filename (มีอยู่แล้ว)
2. **Per-user isolation** — vault file query ต้อง `WHERE user_id = current_user.id`
3. **Cascade delete** — ลบ vault file = cascade FK เหมือน processed
4. **Best-effort BYOS** — Drive push fail ไม่ block upload

### Gotchas
1. **Order ของ check ใน upload** — sequence ต้องเป็น:
   ```
   ext check → vault flag (อย่าง continue ที่นี่)
   quota check → SKIP QUOTA_EXCEEDED
   read bytes
   empty check → SKIP EMPTY_FILE
   size check → SKIP FILE_TOO_LARGE
   save raw → extract (ถ้า not vault)
   ```
2. **classify_extraction_status with empty text** — return "empty" ปัจจุบัน — vault ต้อง override เป็น "vault" ก่อน save
3. **Migration backfill** — existing rows มี `file_kind=NULL` หลัง ALTER COLUMN — column default ใช้กับ INSERT ใหม่เท่านั้น **ต้อง UPDATE** existing → "processed"
   ```sql
   UPDATE files SET file_kind='processed' WHERE file_kind IS NULL;
   ```
4. **Frontend filter state persists** — เก็บใน localStorage `pdb_files_filter_kind` เพื่อ user reload ไม่หาย
5. **List endpoint Query param validation** — ใช้ FastAPI Query regex กัน injection
6. **Dedupe avoid duplicate** — ถ้า user upload .pdf ซ้ำ + .zip ซ้ำ พร้อมกัน → semantic dedupe ใช้ได้กับ pdf, ไม่ใช้กับ vault (Q6)
7. **Reprocess endpoint vs Promote endpoint** — แยกต่างกัน:
   - `reprocess` (มีอยู่) = re-extract processed file (ถ้าเสีย)
   - `promote` (ใหม่) = vault → processed (ลอง extract ครั้งแรก)
8. **GOOGLE_API_KEY check** — promote สำหรับ audio/video → ตรวจ ai_ingest.is_available() ก่อน

### Test ก่อน commit
```bash
python -m pytest tests/test_raw_vault_v910.py -v
python scripts/raw_vault_e2e_verify.py
# regression
python scripts/dedupe_e2e_verify.py
python scripts/upload_resilience_e2e_verify.py
python scripts/byos_foundation_smoke.py
# ... ฯลฯ ครบ 7 suites
npx playwright test --config=playwright.config.standalone.js
```

### Pipeline state ที่จะ update
- ก่อน build: `building`
- หลัง build เสร็จ: `built_pending_review`
- ฟ้า approve: `done`

---

## 📅 Timeline

| Phase | Build | Test | Total |
|-------|-------|------|-------|
| Step 1: Migration | 30 นาที | 15 นาที | 45 นาที |
| Step 2-7: Backend (upload + endpoints + filter) | 2 ชม. | 30 นาที | 2.5 ชม. |
| Step 8: BYOS folder | 30 นาที | 15 นาที | 45 นาที |
| Step 9: Frontend (chips + badge + promote) | 1.5 ชม. | 30 นาที | 2 ชม. |
| Tests (Layer 1+2+3) | — | 1.5 ชม. | 1.5 ชม. |
| **Total** | **4.5 ชม.** | **3 ชม.** | **~7-8 ชม.** |

---

## 🚦 Acceptance Criteria สรุป

ก่อน user approve plan + ก่อน เขียวเริ่ม build:

- [ ] User ตอบ Q1-Q8 (หรือเลือก "ตามที่แดงแนะนำ")
- [ ] User ยืนยันว่า scope = vault behavior + filter UI + promote button (ไม่รวม auto-promote, raw_hash dedupe)
- [ ] User ยืนยันว่า quota ใช้รวมกัน (Free 50 ไฟล์ = vault + processed รวม)

หลังเขียวเสร็จ:

- [ ] All test layers pass (target ~75 new + 238 regression)
- [ ] Migration verified idempotent
- [ ] Manual smoke 6 items confirmed
- [ ] No regression ใน organize/chat/cluster (vault excluded)
