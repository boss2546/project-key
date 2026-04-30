# Plan: Google Drive BYOS — Bring Your Own Storage

**Author:** แดง (Daeng)
**Date:** 2026-04-30
**Status:** draft (รอ user approve)
**Estimated effort:** เขียว 1 week (ทีมเก่ง) + ฟ้า 2-3 วัน + ⚠️ **NO verification** during MVP

**Updated 2026-04-30 v2 (FINAL strategy):**
- User ตัดสินใจ skip Google verification สำหรับ MVP
- เหตุผล: ยังไม่ขายจริง — ทดสอบภายใน + คนที่รู้จัก
- Strategy: ใช้ **Testing Mode** (ไม่ใช่ Production-Unverified) — clean UX, ไม่มี warning
- Verification จะ submit ภายหลังเมื่อพร้อม public launch
- **Internal beta launch ภายใน 1 สัปดาห์!**

---

## 🎯 Goal

ให้ลูกค้า **เลือกได้** ว่าจะเก็บไฟล์/ข้อมูลส่วนตัวไว้ที่ไหน:
1. **Managed Mode** (ปัจจุบัน) — Project KEY เก็บใน server ของบริษัทบน Fly.io volume
2. **BYOS Mode** (ใหม่) — เก็บใน Google Drive ของลูกค้าเอง, server ของเราทำหน้าที่ "index + cache" เพื่อความเร็ว

**โมเดล: "Hybrid — Drive = Truth, Server = Index" (จากคุย user 2026-04-30)**
- ของจริงทุกชิ้น (raw files, summaries, profile, graph) → อยู่ใน Drive ของ user ใน folder `/Project KEY/`
- Index + cache → SQLite บน server เพื่อ search/query เร็ว
- Cache สามารถ rebuild ได้ 100% จาก Drive ถ้าหาย
- 2-way sync: user แก้ผ่าน Project KEY UI หรือ แก้ใน Drive โดยตรง — ทั้ง 2 ทางทำงานได้

**ผู้ใช้:**
- Privacy-conscious users — อยาก control ข้อมูลตัวเอง
- Power users ที่อยากเปิด Drive ดูข้อมูลเองได้
- Workspace users ที่นโยบายบริษัทกำหนดให้ข้อมูลต้องอยู่ใน Workspace ของตัวเอง

**ทำเสร็จแล้วได้อะไร:**
1. **Differentiator ที่ Claude/ChatGPT/Notion AI ไม่มี** — "Your data stays in YOUR Drive"
2. **PDPA-friendly** — ระบุได้ชัดว่าเรา process แต่ไม่ store user content
3. **User-sovereign** — ถ้า Project KEY ปิดบริการ user ยังมีข้อมูลครบใน Drive
4. **Marketing pitch:** "Open your Drive right now and verify — we hide nothing"
5. **Backup ฟรี** — Drive ของ user คือ backup ของระบบโดยอัตโนมัติ
6. **Path เปิดสำหรับ feature อื่น** — Notion BYOS, Dropbox BYOS, GitHub BYOS ในอนาคต

---

## ✅ Resolved Decisions (จาก user 2026-04-30)

| # | Decision | สถานะใน plan |
|---|---|---|
| Q1 | **Coexist** — Managed Mode + BYOS Mode | ✅ บาก-in |
| Q2 | **`drive.file` + Google Picker** (drive เต็มไว้ phase 2) | ✅ บาก-in |
| Q3 | **Transparent JSON** — ไม่ encrypt (debug ง่าย + trust สูง) | ✅ บาก-in |
| Q4 | **2-way sync** — upload ผ่านเราก็ได้, แก้ใน Drive ก็ได้ | ✅ บาก-in |

---

## 📚 Context

### Architecture ปัจจุบัน (Managed Mode)
- ทุกอย่างเก็บใน Fly.io volume `/app/data/`:
  - `projectkey.db` — SQLite (metadata, summaries, profile, graph, vector index)
  - `uploads/{user_id}/` — raw files
  - `summaries/`, `context_packs/`, `chroma_db/` — derived data
- Single source of truth = server volume
- ถ้า Fly.io volume เสีย → backup จะกู้คืน (มี [database.py:417](../../backend/database.py#L417) auto-backup)

### Architecture ใหม่ (BYOS Mode) — Hybrid

```
┌─────────────────────────────────────────────────────────────┐
│ User's Google Drive (Truth)                                  │
│ /Project KEY/                                                │
│   ├── raw/                  ← ไฟล์ต้นฉบับ (PDF, DOCX, etc.) │
│   ├── extracted/            ← extracted text (.txt)          │
│   ├── summaries/            ← AI summaries (.md)             │
│   ├── personal/                                              │
│   │   ├── profile.json      ← MBTI, Enneagram, identity     │
│   │   └── contexts.json     ← context memory                 │
│   ├── data/                                                  │
│   │   ├── clusters.json     ← collections                    │
│   │   ├── graph.json        ← knowledge graph                │
│   │   └── relations.json                                     │
│   └── _meta/                                                 │
│       ├── manifest.json     ← file index for self-recovery  │
│       └── version.txt       ← schema version (สำหรับ migrate)│
└─────────────────────────────────────────────────────────────┘
                            ↕ sync
┌─────────────────────────────────────────────────────────────┐
│ Project KEY Server (Cache + Index)                           │
│ SQLite — เก็บแค่:                                            │
│   • user account + OAuth refresh_token (encrypted)           │
│   • storage_mode = "managed" | "byos"                        │
│   • drive_connection (drive_email, last_sync_at)             │
│   • files index (file_id ↔ drive_file_id, hash, modified)   │
│   • vector embeddings (rebuilt-able from Drive)              │
│   • personality cache (denorm จาก profile.json)              │
│   • graph cache (load จาก graph.json on demand)              │
│   • All cached data marked with `synced_from_drive_at`       │
└─────────────────────────────────────────────────────────────┘
```

### Key principles
1. **Drive = source of truth** — ถ้า Drive ขัดแย้งกับ cache, Drive ชนะ
2. **Cache = rebuildable** — ถ้า cache หาย, resync จาก Drive ภายใน 1-5 นาที (ขึ้นกับขนาด)
3. **Coexist** — user เลือก mode ตอน register หรือเปลี่ยนใน profile
4. **Migrate-able** — user เปลี่ยน mode ได้ (Managed → BYOS หรือกลับ)

### OAuth strategy: `drive.file` + Picker
- App สร้าง `/Project KEY/` folder อัตโนมัติ → access ทุกไฟล์ใน folder นั้น
- User เลือกไฟล์เพิ่มจาก Drive อื่น → ผ่าน Picker
- Verification ฟรี ~2-4 weeks (vs `drive` เต็ม $25K-85K + 6 เดือน)

---

## 📁 Files to Create / Modify

### Backend (สร้างใหม่ 4 + แก้ 6)
- [ ] `backend/drive_oauth.py` (**create**) — OAuth 2.0 flow + token storage + refresh logic
- [ ] `backend/drive_storage.py` (**create**) — Drive API CRUD wrapper (upload/download/list/delete)
- [ ] `backend/drive_sync.py` (**create**) — sync orchestration (Drive ↔ SQLite cache)
- [ ] `backend/drive_layout.py` (**create**) — folder structure constants + path helpers
- [ ] `backend/database.py` (modify) — add `DriveConnection` table + `User.storage_mode` column + migration
- [ ] `backend/main.py` (modify) — new endpoints (oauth init/callback, picker session, mode switch, manual sync trigger) + storage-mode-aware existing endpoints
- [ ] `backend/config.py` (modify) — `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI`
- [ ] `backend/extraction.py` (modify) — accept Drive-sourced files (download bytes → extract → return text)
- [ ] `backend/profile.py` (modify) — read/write profile.json on Drive when storage_mode=byos
- [ ] `backend/organizer.py` (modify) — write summaries to Drive when storage_mode=byos
- [ ] `backend/graph_builder.py` (modify) — persist graph.json to Drive when storage_mode=byos

### Frontend (สร้างใหม่ 1 + แก้ 3)
- [ ] `legacy-frontend/storage_mode.js` (**create**) — module สำหรับ BYOS mode logic + Picker
- [ ] `legacy-frontend/index.html` (modify) — Storage Mode section ใน profile-modal + connect/disconnect UI + Picker container
- [ ] `legacy-frontend/app.js` (modify) — OAuth callback handler + mode-aware upload + sync status indicator
- [ ] `legacy-frontend/styles.css` (modify) — style storage mode UI

### Tests (สำหรับฟ้า — create)
- [ ] `tests/test_drive_oauth.py` — OAuth flow + token refresh + revocation
- [ ] `tests/test_drive_storage.py` — CRUD operations (with Drive API mocked)
- [ ] `tests/test_drive_sync.py` — sync logic (Drive → cache, cache → Drive, conflict resolution)
- [ ] `tests/test_byos_mode_switch.py` — Managed ↔ BYOS migration
- [ ] `tests/e2e/test_byos_e2e.py` — full E2E flow

### Memory updates
- [ ] `.agent-memory/contracts/api-spec.md` — document new endpoints
- [ ] `.agent-memory/contracts/data-models.md` — document Drive folder structure + DriveConnection schema

---

## 💾 Data Model Changes

### A) Extend `users` table
```python
class User(Base):
    # existing fields...
    storage_mode = Column(String, default="managed")
    # "managed" | "byos"
    # default = "managed" (backward compat สำหรับ user เดิม)
```

### B) NEW table `drive_connections`
```python
class DriveConnection(Base):
    """OAuth connection to user's Google Drive."""
    __tablename__ = "drive_connections"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    drive_email = Column(String, nullable=False)
    refresh_token_encrypted = Column(Text, nullable=False)
    # encrypted with Fernet (key in env: DRIVE_TOKEN_ENCRYPTION_KEY)
    drive_root_folder_id = Column(String, nullable=False)
    # folder ID ของ /Project KEY/ ใน Drive ของ user
    last_sync_at = Column(DateTime, nullable=True)
    last_sync_status = Column(String, default="pending")
    # "pending" | "syncing" | "success" | "error"
    last_sync_error = Column(Text, nullable=True)
    connected_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)

    user = relationship("User", backref=backref("drive_connection", uselist=False))
```

### C) Extend `files` table
```python
class File(Base):
    # existing fields...
    drive_file_id = Column(String, nullable=True, index=True)
    # Google Drive file ID (NULL ถ้า managed mode)
    drive_modified_time = Column(DateTime, nullable=True)
    # last modifiedTime จาก Drive (used for sync drift detection)
    storage_source = Column(String, default="local")
    # "local" | "drive_uploaded" | "drive_picked"
    # local = managed mode
    # drive_uploaded = user upload ผ่าน UI → ไปอยู่ใน Drive
    # drive_picked = user pick ไฟล์ที่มีอยู่ใน Drive แล้ว
```

### D) Migration (in `database.py:init_db()`)

```python
# v6.1 Migration — BYOS support
cursor = await db.execute("PRAGMA table_info(users)")
user_cols = [row[1] for row in await cursor.fetchall()]
if "storage_mode" not in user_cols:
    await db.execute("ALTER TABLE users ADD COLUMN storage_mode TEXT DEFAULT 'managed'")
    migrated = True

cursor = await db.execute("PRAGMA table_info(files)")
file_cols = [row[1] for row in await cursor.fetchall()]
if "drive_file_id" not in file_cols:
    await db.execute("ALTER TABLE files ADD COLUMN drive_file_id TEXT")
    await db.execute("ALTER TABLE files ADD COLUMN drive_modified_time TEXT")
    await db.execute("ALTER TABLE files ADD COLUMN storage_source TEXT DEFAULT 'local'")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_files_drive_file_id ON files(drive_file_id)")
    migrated = True

# drive_connections table created via Base.metadata.create_all()
```

---

## 📂 Drive Folder Structure (Source of Truth)

```
/Project KEY/                          ← root (created on first connection)
├── _meta/
│   ├── version.txt                    ← schema version (e.g., "1.0")
│   └── manifest.json                  ← list of all files + their roles
│
├── raw/                               ← original files (preserved)
│   ├── {file_id}_{original_name}.pdf
│   ├── {file_id}_{original_name}.docx
│   └── ...
│
├── extracted/                         ← extracted plain text
│   ├── {file_id}.txt
│   └── ...
│
├── summaries/                         ← AI-generated summaries
│   ├── {file_id}.md                   ← formatted markdown
│   └── ...
│
├── personal/
│   ├── profile.json                   ← personality + identity
│   └── contexts.json                  ← context memory
│
├── data/
│   ├── clusters.json                  ← collections
│   ├── graph.json                     ← knowledge graph
│   ├── relations.json                 ← relations + suggestions
│   └── chat_history.json              ← optional, last 100 chats
│
└── _backups/                          ← auto-rotated backups
    ├── 2026-04-30_03-00.zip
    └── ...
```

### Schema versioning
- `_meta/version.txt` มี เลข version ของ folder structure
- ถ้า version ของ Project KEY ใหม่กว่า → migrate folder layout
- Backward compat: app version ใหม่อ่าน version เก่าได้

---

## 📡 API Changes

### A) OAuth flow

#### `GET /api/drive/oauth/init`
**Auth:** Required (JWT)
**Response 200:**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/auth?client_id=...&scope=drive.file&...&state=..."
}
```
Frontend redirects to `auth_url` → user grants → Google redirects to callback

#### `GET /api/drive/oauth/callback?code=...&state=...`
**Auth:** None (Google redirects here, validated via `state` token)
**Logic:**
1. Validate state (CSRF protection — state matches user's session)
2. Exchange code → access_token + refresh_token via Google
3. Encrypt refresh_token, save to `drive_connections`
4. Create `/Project KEY/` folder if not exists
5. Save folder_id
6. Redirect to frontend with success param: `/legacy?drive_connected=true`

#### `POST /api/drive/disconnect`
**Auth:** Required (JWT)
**Logic:**
1. Revoke OAuth token via Google API
2. Delete `drive_connections` row
3. Choose: `keep_files: true | false`
   - `keep_files=true`: server cache stays, but read-only (sync stops)
   - `keep_files=false`: delete all File rows linked to Drive (server side; Drive content untouched)

**Response 200:** `{"status": "disconnected"}`

### B) Storage mode switch

#### `PUT /api/storage-mode`
**Auth:** Required (JWT)
**Body:** `{"mode": "managed" | "byos"}`
**Errors:**
- 400 `BYOS_REQUIRES_DRIVE_CONNECTION` — switch to byos แต่ไม่มี drive_connection
- 400 `MIGRATION_IN_PROGRESS` — กำลัง migrate อยู่ ห้ามเปลี่ยน mode ระหว่างทาง

**Behavior:**
- managed → byos: trigger background migration job (upload local files to Drive)
- byos → managed: trigger background migration job (download Drive files to local)
- จะส่ง email/in-app notification เมื่อ migrate เสร็จ

### C) Picker integration

#### `POST /api/drive/picker/session`
**Auth:** Required (JWT, byos mode)
**Response 200:**
```json
{
  "oauth_token": "ya29.a0...",
  "developer_key": "AIza...",
  "app_id": "..."
}
```
Frontend ใช้ token นี้ initialize Picker UI → user เลือกไฟล์ → callback ส่ง file IDs กลับ

#### `POST /api/drive/import`
**Auth:** Required (JWT, byos mode)
**Body:** `{"drive_file_ids": ["1AbC...", "2DeF..."]}`
**Logic:**
1. For each file_id:
   - Download from Drive
   - Extract text (existing extraction.py)
   - Save to user's `/Project KEY/extracted/` and `/Project KEY/raw/`
   - Create File row with `drive_file_id` + `storage_source="drive_picked"`
2. Update SQLite cache + vector index
3. Return list of imported files

### D) Sync trigger

#### `POST /api/drive/sync`
**Auth:** Required (JWT, byos mode)
**Body:** `{"force": false}` — true = full re-sync, false = incremental
**Logic:**
1. List `/Project KEY/` recursively from Drive
2. Compare with local files index (`drive_modified_time`)
3. For changed/new: download + re-extract + update cache
4. For deleted: mark File row as deleted
5. Update `drive_connections.last_sync_at`

**Response 200:**
```json
{
  "status": "success",
  "synced_files": 5,
  "new_files": 2,
  "updated_files": 3,
  "deleted_files": 0,
  "duration_ms": 4321
}
```

#### `GET /api/drive/sync/status`
**Response 200:**
```json
{
  "connected": true,
  "drive_email": "user@gmail.com",
  "last_sync_at": "2026-04-30T10:30:00Z",
  "last_sync_status": "success",
  "files_in_drive": 47,
  "files_in_cache": 47,
  "drift_detected": false
}
```

### E) Modified existing endpoints

#### `POST /api/upload` — ตรวจ storage_mode
- **managed mode:** ทำงานเหมือนเดิม (เก็บที่ `uploads/{user_id}/`)
- **byos mode:**
  1. Receive bytes
  2. Extract text (เดิม)
  3. Upload raw → `/Project KEY/raw/{file_id}_{filename}` ใน Drive
  4. Upload extracted → `/Project KEY/extracted/{file_id}.txt`
  5. Save File row with `drive_file_id` + `storage_source="drive_uploaded"`
  6. Update vector index

#### `GET /api/files/{file_id}/download` — ตรวจ storage_mode
- **managed:** serve จาก `raw_path` (เดิม)
- **byos:** redirect ไป Drive direct link หรือ proxy stream จาก Drive API

---

## 🔧 Step-by-Step Implementation (สำหรับเขียว)

### Phase 1: Foundation (Week 1)

#### Step 1.1: Google Cloud Console setup (MVP — Testing Mode)

**สำหรับ MVP เราใช้ Testing Mode — ไม่ใช่ Production!**
- Testing mode = ไม่ต้องมี privacy policy URL, ไม่ต้องมี domain verification, ไม่ต้องมี demo video
- Trade-off: refresh tokens หมดอายุ 7 วัน (ผู้ใช้ re-consent ทุกสัปดาห์)
- เพอร์เฟกต์สำหรับ internal test + closed beta

##### Setup steps (~30 นาที):
1. สร้าง Google Cloud Project "Project KEY BYOS"
2. Enable APIs: Google Drive API, Google Picker API
3. **OAuth Consent Screen → User Type: External, Publishing status: Testing**
   - App name: "Project KEY"
   - User support email: ของคุณ
   - Developer contact: ของคุณ
   - **Test users: เพิ่ม emails ของทีม + beta users** (max 100)
   - ⚠️ ไม่ต้องกรอก privacy policy URL, ไม่ต้อง app domain
4. Create OAuth 2.0 Client ID (Web application)
   - Authorized origins: `https://project-key.fly.dev`, `http://localhost:8000`
   - Authorized redirect URIs: `https://project-key.fly.dev/api/drive/oauth/callback`, `http://localhost:8000/api/drive/oauth/callback`
5. Create API key for Picker (restrict to Drive API + HTTP referrer)
6. Set env vars in Fly.io:
   ```
   GOOGLE_OAUTH_CLIENT_ID=...
   GOOGLE_OAUTH_CLIENT_SECRET=...
   GOOGLE_PICKER_API_KEY=...
   GOOGLE_PICKER_APP_ID=...   # = project number
   DRIVE_TOKEN_ENCRYPTION_KEY=...   # generate via cryptography.fernet.Fernet.generate_key()
   GOOGLE_OAUTH_MODE=testing   # หรือ 'production' ภายหลัง
   ```

##### Frontend reminder banner (สำคัญ!)
แสดงในหน้า Drive Settings:
```
⚠️ Beta Mode: Project KEY ยังอยู่ใน Google testing mode
   - คุณต้อง re-connect Drive ทุก 7 วัน
   - เฉพาะผู้ที่ได้รับเชิญเท่านั้น
   - หลัง launch สาธารณะ → ใช้งานต่อเนื่อง ไม่ต้อง re-connect
```

#### Step 1.2: OAuth verification submission (parallel — เริ่ม Day 0!)

> 🔥 **CRITICAL:** เริ่มทำพร้อมกันกับ dev — ไม่ใช่หลัง dev เสร็จ
> เพราะ Google ตรวจสอบ 2-4 สัปดาห์ controllable ไม่ได้

##### Materials checklist
1. **Privacy Policy** → `/privacy` page
   - public URL, no login
   - ระบุ: ข้อมูลที่เก็บ (refresh_token, extracted text, metadata), retention, sharing, deletion
   - Time: 2-4 hr drafting
2. **Terms of Service** → `/terms` page
   - มาตรฐาน + section เกี่ยวกับ Google scope use
   - Time: 2-3 hr
3. **Domain verification** via Google Search Console
   - Add `project-key.fly.dev`
   - Time: ~1 hr (DNS propagation)
4. **OAuth consent screen setup**
   - Logo (PNG, 120x120)
   - App name: "Project KEY"
   - Support email + developer contact email
   - Authorized domains
   - Time: ~30 min
5. **Demo video** (1-2 min, YouTube unlisted หรือ Loom)
   - User คลิก "Connect Drive"
   - OAuth screen
   - Picker เลือกไฟล์
   - ไฟล์ปรากฏใน Project KEY UI
   - แสดงปุ่ม disconnect + ผลที่เกิดขึ้น
   - Narration ภาษาอังกฤษ (Google reviewer ใช้ EN)
   - Time: 2-4 hr (ถ่าย + edit)
6. **Scope justification doc**
   ```
   Why drive.file:
   - Allow users to select specific files from their Drive
     for AI-powered text analysis and personal organization.
   - We do NOT access files outside our app's /Project KEY/
     folder or files not explicitly picked by user.
   - We extract text content for AI analysis but do not
     redistribute file content to third parties.
   - Refresh tokens are encrypted at rest with AES-256.
   - Users can revoke access anytime; revocation deletes
     all server-side cached data immediately.
   ```
7. **Submit for verification** ผ่าน Google Cloud Console

##### ระหว่างรอ Google (2-4 สัปดาห์):

###### Mode A: Production-Unverified
- App ใช้งานได้, แต่แสดง **"Unverified app" warning** 3 หน้าจอก่อน Allow
- Cap **100 users lifetime** (unique Google accounts ที่ Allow)
- ✅ Refresh tokens ไม่หมดอายุ (production tokens)
- ⚠️ Conversion rate ตก ~50-70% เพราะ warning น่ากลัว
- เหมาะกับ: early adopters / closed beta ที่ความ tech-savvy

###### Mode B: Test Users (แนะนำสำหรับ closed beta!)
- Add max **100 emails** ใน OAuth consent screen → "Test users" section
- ✅ **ไม่มี warning** — ลูกค้าเห็น OAuth screen ปกติ
- ✅ User experience สมบูรณ์
- ⚠️ Refresh tokens **หมดอายุภายใน 7 วัน** → user re-consent ทุกสัปดาห์
- เหมาะกับ: pre-screened users ที่ยอมรับ inconvenience นี้

> 💡 **Best practice:** ใช้ Mode B สำหรับ 50-100 users แรกที่รู้จัก (founder's friends, paying beta users).
> ใช้ Mode A หลัง Google reviewer started (กำลัง review = ความน่าจะ approved สูง)
> หลัง verified → switch to Production mode → no warning + no cap

#### Step 1.3: Backend foundation
1. สร้าง `backend/drive_oauth.py`:
   ```python
   """Google Drive OAuth 2.0 flow."""
   from google_auth_oauthlib.flow import Flow
   from cryptography.fernet import Fernet
   import secrets

   SCOPES = ["https://www.googleapis.com/auth/drive.file"]

   def build_oauth_flow(redirect_uri: str) -> Flow:
       return Flow.from_client_config(
           {"web": {
               "client_id": GOOGLE_OAUTH_CLIENT_ID,
               "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
               "auth_uri": "https://accounts.google.com/o/oauth2/auth",
               "token_uri": "https://oauth2.googleapis.com/token",
               "redirect_uris": [redirect_uri],
           }},
           scopes=SCOPES,
       )

   def encrypt_token(token: str) -> str:
       return Fernet(DRIVE_TOKEN_ENCRYPTION_KEY.encode()).encrypt(token.encode()).decode()

   def decrypt_token(encrypted: str) -> str:
       return Fernet(DRIVE_TOKEN_ENCRYPTION_KEY.encode()).decrypt(encrypted.encode()).decode()

   async def init_oauth(user_id: str) -> dict:
       """Generate auth URL with state CSRF token."""
       flow = build_oauth_flow(...)
       state = secrets.token_urlsafe(32)
       # save state in cache (Redis or in-memory dict with TTL 10 min)
       _STATE_CACHE[state] = {"user_id": user_id, "expires": time.time() + 600}
       auth_url, _ = flow.authorization_url(
           access_type="offline",   # request refresh_token
           prompt="consent",         # force consent screen
           state=state,
       )
       return {"auth_url": auth_url}

   async def handle_callback(code: str, state: str, db: AsyncSession) -> str:
       """Exchange code for tokens, save to DB."""
       state_info = _STATE_CACHE.pop(state, None)
       if not state_info or state_info["expires"] < time.time():
           raise HTTPException(400, "INVALID_OAUTH_STATE")

       flow = build_oauth_flow(...)
       flow.fetch_token(code=code)
       creds = flow.credentials

       # Get user's Drive email
       from googleapiclient.discovery import build
       service = build("drive", "v3", credentials=creds)
       about = service.about().get(fields="user").execute()
       drive_email = about["user"]["emailAddress"]

       # Create root folder
       root_folder = service.files().create(
           body={"name": "Project KEY", "mimeType": "application/vnd.google-apps.folder"},
           fields="id",
       ).execute()
       root_id = root_folder["id"]

       # Save connection
       conn = DriveConnection(
           user_id=state_info["user_id"],
           drive_email=drive_email,
           refresh_token_encrypted=encrypt_token(creds.refresh_token),
           drive_root_folder_id=root_id,
       )
       db.add(conn)
       await db.commit()

       return state_info["user_id"]
   ```

2. สร้าง `backend/drive_storage.py`:
   ```python
   """Wrapper for Drive API operations."""
   from google.auth.transport.requests import Request
   from google.oauth2.credentials import Credentials
   from googleapiclient.discovery import build
   from googleapiclient.http import MediaIoBaseUpload
   import io

   class DriveClient:
       def __init__(self, refresh_token: str):
           self.creds = Credentials(
               token=None,
               refresh_token=refresh_token,
               token_uri="https://oauth2.googleapis.com/token",
               client_id=GOOGLE_OAUTH_CLIENT_ID,
               client_secret=GOOGLE_OAUTH_CLIENT_SECRET,
           )
           self.creds.refresh(Request())  # get fresh access_token
           self.service = build("drive", "v3", credentials=self.creds)

       def upload_file(self, parent_folder_id: str, name: str, content: bytes, mime_type: str) -> str:
           """Upload bytes as file, return drive_file_id."""
           media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type, resumable=True)
           result = self.service.files().create(
               body={"name": name, "parents": [parent_folder_id]},
               media_body=media,
               fields="id",
           ).execute()
           return result["id"]

       def download_file(self, file_id: str) -> bytes:
           return self.service.files().get_media(fileId=file_id).execute()

       def list_files(self, parent_folder_id: str) -> list[dict]:
           result = self.service.files().list(
               q=f"'{parent_folder_id}' in parents and trashed=false",
               fields="files(id, name, mimeType, modifiedTime, size)",
           ).execute()
           return result.get("files", [])

       def get_metadata(self, file_id: str) -> dict:
           return self.service.files().get(fileId=file_id, fields="id, name, mimeType, modifiedTime").execute()

       def delete_file(self, file_id: str):
           self.service.files().delete(fileId=file_id).execute()

       def ensure_folder(self, parent_id: str, name: str) -> str:
           """Get folder ID, create if not exists."""
           q = f"'{parent_id}' in parents and name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
           result = self.service.files().list(q=q, fields="files(id)").execute()
           if result.get("files"):
               return result["files"][0]["id"]
           folder = self.service.files().create(
               body={"name": name, "parents": [parent_id], "mimeType": "application/vnd.google-apps.folder"},
               fields="id",
           ).execute()
           return folder["id"]
   ```

3. สร้าง `backend/drive_layout.py`:
   ```python
   """Drive folder layout constants."""
   FOLDERS = {
       "raw": "raw",
       "extracted": "extracted",
       "summaries": "summaries",
       "personal": "personal",
       "data": "data",
       "_meta": "_meta",
       "_backups": "_backups",
   }

   FILES = {
       "manifest": "_meta/manifest.json",
       "version": "_meta/version.txt",
       "profile": "personal/profile.json",
       "contexts": "personal/contexts.json",
       "clusters": "data/clusters.json",
       "graph": "data/graph.json",
       "relations": "data/relations.json",
       "chat_history": "data/chat_history.json",
   }

   SCHEMA_VERSION = "1.0"

   def raw_path(file_id: str, filename: str) -> str:
       return f"raw/{file_id}_{filename}"

   def extracted_path(file_id: str) -> str:
       return f"extracted/{file_id}.txt"

   def summary_path(file_id: str) -> str:
       return f"summaries/{file_id}.md"
   ```

### Phase 2: Mode switch + Upload (Week 2)

#### Step 2.1: Storage mode plumbing
1. Add `storage_mode` column to User (migration)
2. Helper: `def get_user_storage_mode(user) -> Literal["managed", "byos"]`
3. ใน `backend/main.py` POST `/api/upload`:
   ```python
   if user.storage_mode == "byos":
       # save to Drive
       conn = await get_drive_connection(db, user.id)
       client = DriveClient(decrypt_token(conn.refresh_token_encrypted))
       raw_folder_id = client.ensure_folder(conn.drive_root_folder_id, "raw")
       drive_file_id = client.upload_file(raw_folder_id, f"{file_id}_{filename}", content, mime_type)
       extracted_folder_id = client.ensure_folder(conn.drive_root_folder_id, "extracted")
       client.upload_file(extracted_folder_id, f"{file_id}.txt", extracted_text.encode(), "text/plain")
       file = File(
           id=file_id, user_id=user.id, filename=filename,
           drive_file_id=drive_file_id,
           storage_source="drive_uploaded",
           extracted_text=extracted_text,  # cache in DB
           # raw_path = NULL (อยู่ใน Drive)
       )
   else:
       # existing managed mode logic
   ```

4. POST `/api/storage-mode` endpoint — ดู API spec ข้างบน

#### Step 2.2: Picker integration
1. Frontend `storage_mode.js`:
   ```javascript
   async function openDrivePicker() {
     // Get session token
     const res = await authFetch('/api/drive/picker/session', {method: 'POST'});
     const {oauth_token, developer_key, app_id} = await res.json();

     // Load Picker API
     await loadGooglePickerSDK();

     // Build picker
     const view = new google.picker.DocsView()
       .setIncludeFolders(false)
       .setMimeTypes('application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown');

     const picker = new google.picker.PickerBuilder()
       .addView(view)
       .setOAuthToken(oauth_token)
       .setDeveloperKey(developer_key)
       .setAppId(app_id)
       .setCallback(handlePickerCallback)
       .build();

     picker.setVisible(true);
   }

   async function handlePickerCallback(data) {
     if (data.action === 'picked') {
       const fileIds = data.docs.map(d => d.id);
       const res = await authFetch('/api/drive/import', {
         method: 'POST',
         headers: {'Content-Type': 'application/json'},
         body: JSON.stringify({drive_file_ids: fileIds})
       });
       // refresh file list
     }
   }
   ```

### Phase 3: 2-way Sync (Week 3)

#### Step 3.1: Sync engine
1. สร้าง `backend/drive_sync.py`:
   ```python
   async def sync_user_drive(db: AsyncSession, user_id: str, force: bool = False) -> dict:
       """Sync between Drive (truth) and SQLite cache.

       Strategy:
       - List all files in Drive /Project KEY/
       - For each: compare modifiedTime with cache.drive_modified_time
       - If newer in Drive: download + re-extract + update cache
       - If file in cache but not in Drive: mark deleted (or delete cache row)
       - If file in Drive but not in cache: insert cache row
       """
       conn = await get_drive_connection(db, user_id)
       client = DriveClient(decrypt_token(conn.refresh_token_encrypted))

       # 1. List Drive
       raw_folder = client.ensure_folder(conn.drive_root_folder_id, "raw")
       drive_files = client.list_files(raw_folder)

       # 2. Build maps
       drive_map = {f["id"]: f for f in drive_files}
       cache_files = (await db.execute(
           select(File).where(File.user_id == user_id, File.drive_file_id != None)
       )).scalars().all()
       cache_map = {f.drive_file_id: f for f in cache_files}

       new_files = []
       updated_files = []
       deleted_files = []

       # 3. Process Drive → Cache
       for drive_id, drive_file in drive_map.items():
           drive_modified = parse_iso(drive_file["modifiedTime"])
           if drive_id not in cache_map:
               # New file in Drive — import
               content = client.download_file(drive_id)
               # ...extract + save File row
               new_files.append(drive_file["name"])
           else:
               cache_file = cache_map[drive_id]
               if not force and cache_file.drive_modified_time and cache_file.drive_modified_time >= drive_modified:
                   continue  # cache up-to-date
               # Updated in Drive — re-fetch
               content = client.download_file(drive_id)
               # ...re-extract + update File row
               cache_file.drive_modified_time = drive_modified
               updated_files.append(drive_file["name"])

       # 4. Process Cache → check for deletes
       for cache_id, cache_file in cache_map.items():
           if cache_id not in drive_map:
               # File deleted in Drive — soft delete cache
               deleted_files.append(cache_file.filename)
               # await db.delete(cache_file)  หรือ mark deleted

       # 5. Update profile.json, graph.json, etc. (similar pattern)
       await sync_personal_files(db, user_id, client, conn)
       await sync_data_files(db, user_id, client, conn)

       # 6. Update connection status
       conn.last_sync_at = datetime.utcnow()
       conn.last_sync_status = "success"
       await db.commit()

       return {
           "status": "success",
           "new_files": len(new_files),
           "updated_files": len(updated_files),
           "deleted_files": len(deleted_files),
       }
   ```

2. Add background sync trigger:
   - **MVP:** Manual sync — user คลิกปุ่ม "🔄 Sync from Drive" ใน UI
   - **Polling:** ตอน user เข้าเว็บ, ถ้า `last_sync_at` เก่ากว่า 5 นาที → sync เงียบๆ background
   - **Phase 2:** Real-time webhook (Drive Push Notifications)

3. POST `/api/drive/sync` endpoint

#### Step 3.2: Conflict resolution
- ถ้า user แก้ไฟล์เดียวกันทั้งใน Drive และผ่าน Project KEY UI
- Strategy: **Drive wins** (last write to Drive)
- ใน Project KEY UI ถ้า detect drift → show "เกิดการเปลี่ยนแปลงใน Drive — กด Sync เพื่ออัปเดต"

### Phase 4: Personal data sync (Week 3.5)

#### Step 4.1: profile.json sync
1. แก้ `backend/profile.py`:
   ```python
   async def get_profile(db, user_id):
       user = await get_user(db, user_id)
       if user.storage_mode == "byos":
           return await get_profile_from_drive(db, user_id)
       # existing managed mode...

   async def get_profile_from_drive(db, user_id):
       # 1. Try cache first (denorm in user_profiles table)
       # 2. If cache stale → fetch from Drive profile.json
       # 3. Update cache + return
       conn = await get_drive_connection(db, user_id)
       client = DriveClient(decrypt_token(conn.refresh_token_encrypted))
       personal_folder = client.ensure_folder(conn.drive_root_folder_id, "personal")
       try:
           profile_id = find_file_by_name(client, personal_folder, "profile.json")
           if profile_id:
               content = client.download_file(profile_id)
               profile_data = json.loads(content)
               # update cache in user_profiles table
               await update_profile_cache(db, user_id, profile_data)
               return profile_data
       except Exception:
           pass
       # fallback to cache
       return await get_profile_from_cache(db, user_id)

   async def update_profile(db, user_id, data):
       # Update cache first
       result = await update_profile_cache(db, user_id, data)
       # If byos → write to Drive
       user = await get_user(db, user_id)
       if user.storage_mode == "byos":
           await write_profile_to_drive(db, user_id, result)
       return result
   ```

#### Step 4.2: graph.json + clusters.json sync (similar pattern)
- ในตอน organize หรือ build_graph เสร็จ → write ผลลัพธ์ลง Drive
- ตอน chat retrieval → load จาก cache ก่อน (เร็ว) → background refresh จาก Drive

### Phase 5: Frontend (Week 4)

#### Step 5.1: Storage Mode UI in Profile Modal

```html
<!-- In profile-modal -->
<details class="storage-mode-section">
  <summary>💾 ที่เก็บข้อมูล</summary>

  <div class="storage-mode-current">
    <div>โหมดปัจจุบัน: <strong id="current-mode">Managed</strong></div>
    <div class="storage-mode-options">
      <label class="mode-option">
        <input type="radio" name="storage-mode" value="managed" checked>
        <div>
          <div class="mode-title">📦 Managed Mode (ปัจจุบัน)</div>
          <div class="mode-desc">Project KEY ดูแลข้อมูลให้ — ใช้งานง่าย ไม่ต้องตั้งค่าอะไรเพิ่ม</div>
        </div>
      </label>
      <label class="mode-option">
        <input type="radio" name="storage-mode" value="byos">
        <div>
          <div class="mode-title">🔵 Bring Your Own Drive (ใหม่!)</div>
          <div class="mode-desc">เก็บข้อมูลใน Google Drive ของคุณ — คุณเป็นเจ้าของ ดูได้ทุกเมื่อ</div>
        </div>
      </label>
    </div>
  </div>

  <div id="drive-connection-block" hidden>
    <div class="drive-not-connected" hidden>
      <p>ยังไม่ได้เชื่อม Google Drive</p>
      <button class="btn btn-primary" id="btn-connect-drive">🔵 เชื่อม Google Drive</button>
    </div>
    <div class="drive-connected" hidden>
      <div>✅ เชื่อมแล้ว: <span id="drive-email"></span></div>
      <div>📁 Root folder: <code>/Project KEY/</code></div>
      <div>🔄 Last sync: <span id="drive-last-sync"></span></div>
      <button class="btn btn-secondary" id="btn-sync-now">🔄 Sync ตอนนี้</button>
      <button class="btn btn-outline" id="btn-disconnect-drive">⏸ ตัดการเชื่อมต่อ</button>
    </div>
  </div>
</details>
```

#### Step 5.2: Connect flow
```javascript
async function connectGoogleDrive() {
  showLoadingOverlay("เชื่อมต่อ Google Drive...");
  const res = await authFetch('/api/drive/oauth/init');
  const {auth_url} = await res.json();
  hideLoadingOverlay();
  // Open in popup or redirect
  window.location.href = auth_url;
}

// On page load — check for ?drive_connected=true
if (new URLSearchParams(window.location.search).get('drive_connected') === 'true') {
  showToast('✅ เชื่อม Google Drive สำเร็จ', 'success');
  // refresh state
}
```

#### Step 5.3: Drive sync indicator
- Header bar: 🔵 (สีฟ้า = synced) / 🟡 (สีเหลือง = drift detected) / 🔴 (สีแดง = error)
- Click → show last sync info + manual sync button

### Phase 6: Testing + Polish (Week 5)

#### Step 6.1: Self-test
- เปิด account ใหม่ → register → connect Drive → upload 5 ไฟล์ → ตรวจ Drive มี folder + ไฟล์ครบ
- เปิด Drive โดยตรง → ลบไฟล์ 1 ไฟล์ → กด Sync ใน Project KEY → ตรวจหายจาก list
- Switch Managed → BYOS → ตรวจไฟล์เดิม upload ขึ้น Drive
- Switch กลับ → ไฟล์ download กลับ local
- Disconnect Drive → ตรวจ token revoked + cache เลือกได้ keep/delete

#### Step 6.2: Error scenarios
- Network down ระหว่าง upload → retry หรือ rollback
- Drive API quota exceeded → graceful degradation (queue + retry)
- Token revoked by user via Google Account → next API call fail → notify user
- /Project KEY/ folder ถูกลบใน Drive → app recreate + restore from cache

---

## 🧪 Test Scenarios (สำหรับฟ้า)

### Happy Path
1. **Register → Connect Drive → Upload**
2. **Pick existing files from Drive**
3. **Switch Managed → BYOS migration**
4. **Edit profile via UI → verify profile.json updated in Drive**
5. **Edit profile.json directly in Drive → sync → cache updated**
6. **Disconnect Drive (keep_files=true)** — server cache stays, sync stops
7. **Disconnect (keep_files=false)** — File rows + Drive folder cleanup

### OAuth Flow
- State CSRF: invalid state → 400
- Code expired → 400
- User denies consent → callback handles gracefully
- Refresh token expired → re-prompt for consent

### Sync Logic
- New file in Drive → next sync imports it
- Modified in Drive → next sync re-extracts + updates
- Deleted in Drive → next sync soft-deletes cache
- Concurrent edit (Drive + UI same minute) → Drive wins
- Drive folder deleted manually → app detects + recreates

### Migration
- Managed → BYOS with 100 files → all upload to Drive successfully
- Migration interrupted halfway → resume on next attempt
- BYOS → Managed → all files download back local

### Edge Cases
- File > 100MB → Drive has 5GB upload limit, OK
- Quota exceeded mid-sync → retry with exponential backoff
- Drive API error 500 → graceful fallback to cache (read-only mode)
- Workspace IT blocks third-party app → user gets clear error

### Plan Limits + Locked Data
- BYOS user downgrade to Free → ไฟล์ใน Drive ของ user ไม่ lock (เป็นของ user) แต่ cache ฝั่งเรา lock ตามปกติ
- ⚠️ ข้อสังเกต: user ที่ downgrade ยังเข้า Drive ของตัวเองได้ → bypass lock ผ่าน Drive
- Solution: lock = mark `is_locked` ใน cache + frontend ซ่อน — แต่ user อยาก bypass ก็เปิด Drive ตัวเองได้ (เป็น expected behavior — ของๆ user)

### Security
- Refresh token encryption key rotation
- HTTPS only in production
- CSRF token in OAuth state
- User can't access another user's Drive (token scoped per user)

---

## ✅ Done Criteria

- [ ] OAuth flow ครบ (init → callback → token storage encrypted → refresh)
- [ ] Picker integration ทำงาน — user pick files from Drive ได้
- [ ] BYOS upload — upload ผ่าน UI ขึ้น Drive folder ถูกต้อง
- [ ] BYOS sync — Drive ↔ cache 2-way ทำงาน
- [ ] Mode switch — Managed ↔ BYOS migrate ครบทุก file
- [ ] Profile/contexts/graph/clusters → save & load จาก Drive ถูกต้อง
- [ ] Disconnect → token revoked + cache cleanup ตามตัวเลือก user
- [ ] OAuth verification submitted (parallel) → ได้ result ก่อน 100 user limit
- [ ] Privacy Policy + Terms of Service published
- [ ] Tests pass (unit + integration + E2E)
- [ ] No regression ใน Managed Mode (existing users ไม่กระทบ)
- [ ] Performance: BYOS chat retrieval ≤ 1.5x ของ Managed
- [ ] Memory updated: api-spec.md, data-models.md, last-session.md, pipeline-state.md

---

## ⚠️ Risks / Open Questions

### Critical Risks
1. **OAuth verification 2-4 weeks** — ต้องเริ่ม submit ทันที parallel กับ dev
   - Mitigation: cap 100 users ตอน "Unverified" → ทำ closed beta กับ 100 users first
2. **Drive API quota** — 1,000 req/100sec/user
   - Mitigation: rate limit ฝั่ง app + caching aggressive
3. **Refresh token revocation** — user revoke ใน Google Account → app ใช้ไม่ได้
   - Mitigation: detect 401 → auto-redirect to re-consent → graceful UX
4. **Cache invalidation bugs** — user แก้ Drive ตรงๆ + cache stale
   - Mitigation: poll-based sync ทุก 5 นาที + manual sync button + drift indicator
5. **Workspace IT block** — corporate Workspace อาจบล็อก third-party
   - Mitigation: clear error message + suggest contact admin
6. **Migration interruption** — user offline กลางคัน migration
   - Mitigation: idempotent migration job + resume from last checkpoint

### UX Risks
7. **User ไม่เข้าใจความต่าง 2 modes** — confused
   - Mitigation: tooltip + "compare modes" link in UI
8. **Migration ใช้เวลานาน** (100 ไฟล์ × 2-3 sec = 5 นาที)
   - Mitigation: progress bar + email notification on complete
9. **Drive folder ลบเสียหายโดยไม่ตั้งใจ**
   - Mitigation: Drive trash 30 วัน + app cache → recovery flow

### Open Questions (รอ user ตัดสิน)
- **Q-A**: Real-time sync via webhook (Drive Push Notifications) — ทำใน MVP หรือ Phase 2?
- **Q-B**: รองรับ Drive ที่มีอยู่แล้ว `/Project KEY/` (จาก app เก่า / sync อื่น) — merge หรือสร้างใหม่?
- **Q-C**: Phase 2: full `drive` scope — เปิดหลัง verify ผ่าน + รายได้พอ (~$25K/yr CASA)?
- **Q-D**: รองรับ Microsoft OneDrive / Dropbox / iCloud ใน Phase 2 ไหม?

### Future Stretch (ทำต่อทีหลัง — ไม่อยู่ใน MVP)
- Real-time webhook sync แทน polling
- Multi-Drive accounts ต่อ user (personal + work)
- E2E encryption mode (Q3 Option C)
- BYOS for Notion / OneDrive / Dropbox
- Backup automation: zip ทุกอย่างใน `/Project KEY/_backups/` ทุกสัปดาห์

---

## 📌 Notes for เขียว

### กฎที่ห้ามลืม
1. **`drive.file` scope = เฉพาะไฟล์ที่ app สร้างเอง หรือ user pick ผ่าน Picker** — ห้ามพยายาม list Drive ทั้งหมด
2. **Encrypt refresh_token เสมอ** ก่อนเก็บใน DB — ใช้ Fernet ใน config: `DRIVE_TOKEN_ENCRYPTION_KEY`
3. **OAuth state CSRF token** ต้องมี — ป้องกัน attacker hijack callback
4. **HTTPS only ในโหมด production** — Google reject HTTP redirect (ยกเว้น localhost)
5. **`Author-Agent: เขียว (Khiao)`** ทุก commit
6. **ห้าม commit `.env`, OAuth credentials, encryption keys**

### Gotchas
- **Refresh token issued ครั้งเดียว** — ตอน first consent. ถ้า user already consented แล้ว Google จะไม่ส่ง refresh_token มาอีก → ต้องใช้ `prompt="consent"` เพื่อบังคับ consent screen
- **Drive folder ID ห้าม hardcode** — เก็บใน `drive_connections.drive_root_folder_id` per user
- **Picker SDK ต้องโหลด async** — `gapi.load('picker', ...)` ก่อนใช้
- **API key ของ Picker ≠ OAuth Client Secret** — เป็น 2 อย่างคนละชนิด
- **Drive รองรับ Google Docs ตามแบบ Google Docs format** — export ต้องใช้ `export()` ไม่ใช่ `get_media()` สำหรับ .gdoc/.gsheet/.gslides
- **JSON files in Drive ใช้ MIME `application/json`** — Drive จะไม่ convert
- **Race condition:** server cache update ก่อน Drive write success → ถ้า Drive fail ต้อง rollback cache → ใช้ "write Drive first, update cache after success" pattern

### Performance tips
- Use `fields=` query parameter เพื่อจำกัด data ที่ Drive ส่งกลับ → เร็วขึ้น 5-10x
- Batch requests: Drive API รองรับ batch endpoint สำหรับ multiple operations ใน 1 request
- Resumable upload สำหรับไฟล์ใหญ่ (>5MB) — `MediaIoBaseUpload(..., resumable=True)`
- Cache OAuth credentials ใน memory (TTL = access_token expiry — 1 ชม.)

### Testing tips
- ใช้ `google-auth-mock` library สำหรับ unit tests
- E2E: ทำ test Google account แยกสำหรับ CI
- ห้าม commit test credentials → ใช้ env var ตอน test

### ขนาด PR ที่คาดไว้
- backend: ~1,200 lines (drive_oauth 250, drive_storage 300, drive_sync 350, modifications 300)
- frontend: ~600 lines (storage_mode.js 250, HTML 100, app.js mods 150, CSS 100)
- tests: ~500 lines (ฟ้าจะเขียน)
- รวม: PR ขนาด **large** — แนะนำแยกเป็น 4 commits:
  1. Schema + foundation (drive_oauth, models)
  2. Drive storage layer + API endpoints
  3. Sync engine + 2-way logic
  4. Frontend + UX polish

### Commit message format
```
feat(byos): Google Drive bring-your-own-storage mode

เพิ่ม Hybrid storage mode — ลูกค้าเลือกได้ว่าจะให้
Project KEY เก็บข้อมูล (Managed) หรือเก็บใน Google Drive
ของตัวเอง (BYOS)

- OAuth 2.0 flow with drive.file scope + Google Picker
- 2-way sync (Drive truth, server index/cache)
- Coexist with existing Managed Mode (no breaking change)
- Migration: Managed ↔ BYOS supported
- Transparent JSON in Drive folder /Project KEY/

Refs: plans/google-drive-byos.md
Author-Agent: เขียว (Khiao)
```

### Pre-launch checklist (เขียวต้องตรวจก่อนส่งฟ้า)
- [ ] OAuth verification submitted to Google
- [ ] Privacy Policy + Terms of Service live
- [ ] Self-test full flow with test Google account
- [ ] Migration tested both directions
- [ ] Disconnect cleanup verified
- [ ] No `.env` / credentials in git
- [ ] Memory files updated
- [ ] Commit messages reference plan
