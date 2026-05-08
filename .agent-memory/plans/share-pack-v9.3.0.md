# Plan: Share Context Pack — v9.3.0 (Detailed Edition)

> **Status:** `plan_pending_approval`
> **Author:** 🔴 แดง (Daeng) — 2026-05-08 (final detailed)
> **Foundation:** v9.2.2 master (after iOS sidebar fix ships)
> **Estimated effort:** เขียว ~2.5 วัน + ฟ้า ~1 วัน
> **Risk:** 🟡 Medium — privacy + clipboard + recipient onboarding flow
>
> **User vision:**
> 1. Sender: กด 📤 = ลิงก์ copy ทันที (default สรุปอย่างเดียว)
> 2. Sender: ติ๊ก "+ แนบไฟล์ทั้งหมด" ได้
> 3. Recipient: เปิดลิงก์ = preview เนื้อหาก่อน (สรุปย่อ + expand) + download ไฟล์แนบได้เลย
> 4. Recipient: ปุ่ม "เก็บเข้าธนาคารข้อมูลของฉัน" → register/login → pack ไปอยู่ใน workspace
> 5. ถ้าไม่เก็บ = ปิด จบ
> 6. ลิงก์ใช้ได้ตลอดจนกว่า revoke
>
> **Verification approach:** ทุก milestone มี **Playwright UI test** ที่รัน real Chromium — ทดสอบทั้ง **ฝั่ง sender** และ **ฝั่ง recipient** end-to-end

---

## 📋 Table of Contents

1. [Goal & Context](#-goal--context)
2. [Files to Create / Modify](#-files-to-create--modify)
3. [Data Model](#-data-model)
4. [API Contracts (Full)](#-api-contracts-full)
5. [Frontend UI Specifications](#-frontend-ui-specifications)
6. [Milestones (7) with Playwright Verification](#-milestones-7-with-playwright-verification)
7. [Comprehensive Test Suite](#-comprehensive-test-suite)
8. [Done Criteria](#-done-criteria)
9. [Risks & Open Questions](#-risks--open-questions)
10. [Notes for เขียว](#-notes-for-เขียว)

---

## 🎯 Goal & Context

### Why
Pack adoption ปัจจุบัน = 0% (149 users, 0 packs in DB). การ share จะเปลี่ยน Pack เป็น **artifact ที่ส่งต่อได้** + เป็น **growth loop** (recipient register PDB ใหม่)

### Goal — 1 ประโยค
**"กด 1 ปุ่มได้ลิงก์ ส่งให้ใครก็ได้ คนรับเปิดดูก่อน ตัดสินใจเก็บเอง"**

### Design decisions (per user 2026-05-07)
| # | Decision |
|---|---|
| Q1 Sender flow | กด 📤 = link copy ทันที (no modal) + bar เล็กเด้งใต้ pack |
| Q2 Files attach | Default = ไม่แนบ ส่ง .md อย่างเดียว · ติ๊กทีเดียว = แนบทุกไฟล์ |
| Q3 Recipient access | ใครมีลิงก์ก็เปิด preview ได้ (no login) |
| Q4 Recipient claim | กด "เก็บ" = ต้อง login PDB → pack clone เข้า workspace |
| Q5 Preview content | สรุปย่อ 300 chars + ปุ่ม "ดูเต็ม" + ดาวน์โหลดไฟล์ได้เลย |
| Q6 TTL | ไม่จำกัด (revoke เอาแทน) |
| Q7 Cloned pack | อิสระจากต้นฉบับ — เจ้าของแก้/revoke = ไม่กระทบของคนรับ |
| Q8 Quota | Free 5 link/เดือน, Starter 50, Admin unlimited |

### Non-goals (เลื่อน v9.4.0+)
- ❌ Email whitelist · TTL slider · Permission tier
- ❌ Subscribe / live update / co-edit
- ❌ MCP create_share tool
- ❌ Email notification

---

## 📁 Files to Create / Modify

| File | Action | Lines | Purpose |
|------|--------|-------|---------|
| `backend/database.py` | modify | +25 | เพิ่ม `class PackShare` + index |
| `backend/pack_share.py` | **NEW** | ~220 | Core: token sign/verify, create/update/revoke share, get_preview, claim_to_workspace |
| `backend/main.py` | modify | +180 | 3 Pydantic models + 5 endpoints + 1 HTML route |
| `backend/context_packs.py` | modify | +8 | `_serialize_pack()` expose `share_count`, `has_active_share` |
| `backend/plan_limits.py` | modify | +30 | `pack_share_limit_monthly` + `check_pack_share_create_allowed` + `get_monthly_pack_share_count` |
| `legacy-frontend/app.html` | modify | +20 | ปุ่ม 📤 ใน pack-card-actions + bar template |
| `legacy-frontend/app.js` | modify | +260 | 6 functions + 14 i18n keys + clipboard |
| `legacy-frontend/styles.css` | modify | +85 | `.pack-share-bar` + animations + locked variant |
| `legacy-frontend/shared_pack.html` | **NEW** | ~180 | Recipient preview page (standalone) |
| `legacy-frontend/shared_pack.js` | **NEW** | ~200 | Render preview + claim button + login flow |
| `legacy-frontend/shared_pack.css` | **NEW** | ~120 | Recipient page styling (responsive) |
| `backend/config.py` + `app.html` | modify | 2 | bump APP_VERSION 9.2.2 → 9.3.0 |
| `scripts/share_pack_smoke.py` | **NEW** | ~280 | 25-case smoke (in-process) |
| `tests/test_share_pack_v9_3.py` | **NEW** | ~450 | 35-case pytest comprehensive |
| `tests/e2e-ui/v9.3.0-share-pack-sender.spec.js` | **NEW** | ~280 | 12 Playwright sender UI tests |
| `tests/e2e-ui/v9.3.0-share-pack-recipient.spec.js` | **NEW** | ~320 | 14 Playwright recipient UI tests |

**Total:** 5 modified + 7 new (~2,460 lines)

**ไม่แตะ:** AI Builder, retriever, graph, MCP, Stripe — out of scope

---

## 🗄️ Data Model

### `PackShare` table — NEW

```python
class PackShare(Base):
    """v9.3.0 — Share link metadata.
    
    Token = JWT signed (scope='pack_share', no exp) — verify ผ่าน DB row check (revoked_at)
    ตัด audit log แยก — view_count + clone_count denormalized พอ"""
    __tablename__ = "pack_shares"
    id = Column(String, primary_key=True, default=gen_id)
    pack_id = Column(String, ForeignKey("context_packs.id"), nullable=False, index=True)
    owner_user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Settings
    include_files = Column(Boolean, default=False)  # default = สรุปอย่างเดียว
    
    # Lifecycle (no TTL — revoke-only)
    revoked_at = Column(DateTime, nullable=True, index=True)
    
    # Stats — denormalized (atomic UPDATE counter)
    view_count = Column(Integer, default=0)
    clone_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    pack = relationship("ContextPack")
    owner = relationship("User")
```

### Migration
- `Base.metadata.create_all` จะสร้างอัตโนมัติ — idempotent
- ไม่ต้อง ALTER existing tables

### `PLAN_LIMITS` — เพิ่ม
```python
"free":    { ..., "pack_share_limit_monthly": 5 },
"starter": { ..., "pack_share_limit_monthly": 50 },
"admin":   { ..., "pack_share_limit_monthly": 999999 },
```

### `UsageLog.action` — value `"pack_share"` (no schema change)

---

## 🔌 API Contracts (Full)

### 1. `POST /api/context-packs/{pack_id}/share` — สร้าง/Get share link

**Auth:** Required (JWT)

**Request:**
```json
{ "include_files": false }
```

**Response 200 (success):**
```json
{
  "share_id": "shr_abc123",
  "share_url": "https://personaldatabank.fly.dev/p/eyJ...",
  "include_files": false,
  "is_new": true,                    // true if just created, false if reused existing
  "view_count": 0,
  "clone_count": 0,
  "created_at": "2026-05-08T..."
}
```

**Behavior:**
1. ถ้า pack มี active share อยู่แล้ว (revoked_at IS NULL) → return เดิม + `is_new=false` (idempotent — ไม่ count quota เพิ่ม)
2. Pre-check: `pack.is_locked` → 400 PACK_LOCKED
3. Pre-check: `check_pack_share_create_allowed` → 403 PACK_SHARE_QUOTA_REACHED (only when creating new)
4. Sign JWT scope=pack_share, payload={share_id} (no exp)
5. log_usage("pack_share") + db.commit()
6. Return share + URL

**Errors:**
- `400 PACK_LOCKED` — pack ถูก lock
- `403 PACK_SHARE_QUOTA_REACHED` — เกินโควต้ารายเดือน
- `404 PACK_NOT_FOUND` — pack ไม่ใช่ของ user

### 2. `PATCH /api/context-packs/shares/{share_id}` — toggle include_files

**Auth:** Required (must be owner)

**Request:** `{ "include_files": true }`

**Response 200:** updated share row

**Behavior:** ตรวจ owner_user_id == current_user.id → update include_files. ไม่นับ quota เพิ่ม. ลิงก์ URL ไม่เปลี่ยน (token เก็บ share_id, ไม่ใช่ include_files)

**Errors:**
- `404 SHARE_NOT_FOUND` (also when not owner — กัน enumeration)

### 3. `DELETE /api/context-packs/shares/{share_id}` — revoke

**Auth:** Required (must be owner)

**Response 200:** `{ "status": "revoked", "share_id": "shr_abc" }`

**Behavior:** Set revoked_at = now. Idempotent (revoke ซ้ำ = no-op return เดิม)

**Errors:**
- `404 SHARE_NOT_FOUND` (also when not owner)

### 4. `GET /api/shared/pack/{token}` — preview (NO AUTH REQUIRED)

**Auth:** None — ใครมีลิงก์ก็เปิดได้

**Response 200:**
```json
{
  "share_id": "shr_abc",
  "pack": {
    "title": "การเรียน Term 2",
    "type": "study",
    "intent": "ใช้ตอบคำถามเรื่องการเรียนเทอมนี้",
    "scope": "เน้นวิชาคำนวณ + ภาษา",
    "summary_short": "<300 chars>",
    "summary_full": "<full text>",
    "owner_name": "Test User",
    "owner_email_masked": "te****@x.com",
    "source_count": 5,
    "created_at": "...",
    "updated_at": "..."
  },
  "files": [                    // empty array if include_files=false
    {
      "file_id": "f1",
      "filename": "calc.pdf",
      "filetype": "pdf",
      "size_bytes": 5000000,
      "download_url": "https://.../d/<signed-token>"
    }
  ],
  "include_files": true,
  "view_count": 4,
  "clone_count": 1
}
```

**Behavior:**
1. Verify JWT (scope=pack_share, no exp check needed)
2. Lookup PackShare by share_id → check `revoked_at IS NULL`
3. Lookup pack → ถ้า pack ลบไปแล้ว → 404 PACK_DELETED
4. Atomic UPDATE: `view_count = view_count + 1`
5. ถ้า include_files=true → generate signed download URLs (TTL 1 hour) สำหรับทุกไฟล์ใน pack.source_file_ids
6. Return response

**Errors:**
- `401 INVALID_TOKEN` — JWT decode fail / wrong scope
- `403 SHARE_REVOKED` — revoked_at != NULL
- `404 SHARE_NOT_FOUND` — share_id ไม่อยู่ใน DB
- `404 PACK_DELETED` — pack ถูกลบ

### 5. `POST /api/shared/pack/{token}/claim` — เก็บเข้า workspace

**Auth:** Required (JWT)

**Request:** `{}` (empty body — token contains everything)

**Response 200:** serialized new ContextPack ที่ recipient เป็นเจ้าของ

**Behavior:**
1. Verify token (เหมือน #4) → check revoked + pack exists
2. Pre-check: `check_pack_create_allowed(current_user)` → 403 PACK_LIMIT_REACHED
3. ถ้า include_files=true:
   - Pre-check: storage quota ของ recipient พอไหม (sum of file sizes)
   - ถ้าไม่พอ → 403 STORAGE_LIMIT_REACHED + แจ้งจำนวนที่ต้องการ
4. สร้าง ContextPack ใหม่ของ current_user:
   - Copy title, type, summary_text
   - intent: เดิม + " (เก็บจาก {owner_name} เมื่อ {YYYY-MM-DD})"
   - scope: เดิม
   - source_file_ids = []
   - source_cluster_ids = []
   - created_via = "shared_clone"
5. ถ้า include_files=true → copy ไฟล์ทั้งหมดเข้า recipient's workspace:
   - Loop pack.source_file_ids
   - shutil.copy raw_path → recipient's UPLOAD_DIR
   - สร้าง File row ใหม่ (user_id=recipient.id, filename, filetype, processing_status="ready", file_kind="processed")
   - update pack.source_file_ids = list of new file ids
6. Atomic UPDATE: `share.clone_count = clone_count + 1`
7. log_usage(recipient.id, "pack_clone")
8. Return cloned pack

**Errors:**
- `401 NOT_AUTHENTICATED` — ไม่มี JWT
- `403 PACK_LIMIT_REACHED` — recipient ครบ quota
- `403 STORAGE_LIMIT_REACHED` — files copy ไม่พอ storage
- `404 SHARE_NOT_FOUND/REVOKED/PACK_DELETED`

### 6. `GET /p/{token}` — Recipient HTML page

**Auth:** None

**Behavior:** Serve `legacy-frontend/shared_pack.html` (static file). JS ใน page ทำ:
1. Read token from URL
2. Fetch `/api/shared/pack/{token}` (no auth)
3. Render preview
4. ถ้ากด "เก็บ" → check localStorage.pdb_token → ถ้าไม่มี → redirect `/?return=/p/{token}&action=claim` (login flow) → กลับมา → POST claim
5. ถ้ามี token → POST `/claim` ทันที

---

## 🎨 Frontend UI Specifications

### Sender — Pack Card (ใน Knowledge → Packs tab)

**ก่อน share:**
```
┌─ Pack: "การเรียน Term 2" ────────────────┐
│ ใช้สำหรับ: ตอบคำถามเรียนเทอมนี้           │
│ [📤] [🔄] [🗑]    ← ปุ่ม share ใหม่ ซ้ายสุด │
│ 5 ไฟล์ • 2 วันก่อน • study               │
└──────────────────────────────────────────┘
```

**หลังกด 📤 (bar เด้งลงมาใต้ pack):**
```
┌─ Pack: "การเรียน Term 2" ────────────────┐
│ ...                              [📤✓]  │ ← ไอคอน checkmark
└──────────────────────────────────────────┘
┌─ Share Link ─────────────────────────────┐
│ 🔗 pdb.fly.dev/p/xK9aB2... [📋 คัดลอก]  │
│ 👁 4 views · 📥 1 clone                   │
│                                          │
│ ☐ + แนบไฟล์ทั้งหมด (5 ไฟล์ · 12 MB)      │
│                                          │
│ [🚫 ยกเลิกลิงก์]              [ปิด ▲]   │
└──────────────────────────────────────────┘
```

**Auto-copy:** ตอนกด 📤 ครั้งแรก → ลิงก์ copy เข้า clipboard ทันที + toast "คัดลอกลิงก์แล้ว"

**Toggle ติ๊ก include_files:**
- ติ๊ก ON → toast "ลิงก์มีไฟล์แนบ 5 ไฟล์" + ลิงก์เดิมยังใช้ได้ + auto-copy ใหม่
- ติ๊ก OFF → toast "ลิงก์เป็นสรุปอย่างเดียวแล้ว" + auto-copy ใหม่

**Confirm dialog ตอนติ๊ก ON ครั้งแรก** (privacy guard):
```
⚠ ยืนยันการแนบไฟล์
จะแนบ 5 ไฟล์ (12 MB) ไปกับลิงก์
ใครเปิดลิงก์จะดาวน์โหลดได้

[ ยกเลิก ]    [ ✓ ใช่ แนบเลย ]
```

### Recipient — `/p/{token}` page

```
┌────────────────────────────────────────────┐
│  📦 Personal Data Bank                     │
│                                            │
│  🎁 มีคนส่ง Pack ให้คุณ                     │
│                                            │
│  ┌─ 📦 การเรียน Term 2 ────────────────┐  │
│  │ จาก: te****@x.com                   │  │
│  │ ประเภท: 📚 study                     │  │
│  │ 👁 4 views · 📥 1 clone                │  │
│  │                                      │  │
│  │ 📋 ใช้สำหรับ:                         │  │
│  │ ตอบคำถามเรื่องการเรียนเทอมนี้           │  │
│  │                                      │  │
│  │ 📦 ครอบคลุม:                          │  │
│  │ เน้นวิชาคำนวณ + ภาษา                  │  │
│  │                                      │  │
│  │ ─── สรุปเนื้อหา ─────────────────  │  │
│  │ Term 2 มีวิชา Calculus,             │  │
│  │ Linear Algebra... (300 chars)        │  │
│  │ [▾ ดูเต็ม]                          │  │
│  │                                      │  │
│  │ 📎 ไฟล์แนบ 5 ไฟล์:                    │  │
│  │ • calc.pdf (5MB)    [⬇ ดาวน์โหลด]   │  │
│  │ • alg.pdf (3MB)     [⬇ ดาวน์โหลด]   │  │
│  │ • notes.md (50KB)   [⬇ ดาวน์โหลด]   │  │
│  │ • essay.docx (2MB)  [⬇ ดาวน์โหลด]   │  │
│  │ • grades.xlsx (8KB) [⬇ ดาวน์โหลด]   │  │
│  └──────────────────────────────────────┘  │
│                                            │
│  ╔══════════════════════════════════════╗  │
│  ║ ➕ เก็บเข้าธนาคารข้อมูลของฉัน         ║  │
│  ╚══════════════════════════════════════╝  │
│                                            │
│  [ ปิดหน้านี้ ]                              │
│                                            │
│  ────────────────────────────────────      │
│  ยังไม่มี Personal Data Bank?                │
│  [ 📝 สมัครฟรี + เก็บ Pack นี้เลย ]         │
└────────────────────────────────────────────┘
```

**Mobile responsive:** card ขยายเต็ม 96vw + button stick top/bottom

**Empty include_files=false:** ซ่อนส่วน "📎 ไฟล์แนบ" ทั้งหมด

**Pack revoked:** แสดง error page:
```
🚫 ลิงก์นี้ถูกยกเลิกแล้ว
เจ้าของยกเลิกการแชร์ pack นี้
[ ไปหน้าหลัก ]
```

### Sidebar/Pack Card Badge (after share active)

```
┌─ Pack: "การเรียน Term 2" 🔗 ─────────────┐  ← icon 🔗 ติด title
│ ...                              [📤✓]   │
│ 5 ไฟล์ · 🔗 4 views · 1 clone            │
└──────────────────────────────────────────┘
```

---

## 📍 Milestones (7) with Playwright Verification

### Milestone 1 — Backend Schema + Token Signing (~3 ชม.)

**Deliverables:**
- `database.py`: `class PackShare` + idempotent migration via `Base.metadata.create_all`
- `pack_share.py`: `sign_share_token(share_id) -> str` + `verify_share_token(token) -> share_id`
- Unit test: token roundtrip + scope validation + tampered token rejection

**Implementation:**
1. เพิ่ม `class PackShare(Base)` ใน database.py ตาม schema ด้านบน
2. สร้าง `backend/pack_share.py`:
   - `_TOKEN_SCOPE = "pack_share"`
   - `sign_share_token(share_id: str) -> str` — JWT no exp, scope=pack_share, payload={share_id, scope, iat}
   - `verify_share_token(token: str) -> str` — return share_id หรือ raise ShareTokenError
3. Run server → check schema created (`PRAGMA table_info(pack_shares)`)

**Playwright verification (M1.spec.js):**
- M1.1: Schema check — call `/api/admin/me` (require admin) → check pack_shares table exists in stats
- M1.2: Token API smoke — sign + verify roundtrip via internal Python test (no UI)

**Pass criteria:** schema migration runs without error, token sign/verify roundtrip works

---

### Milestone 2 — Backend Endpoints (Create + Update + Revoke) (~3 ชม.)

**Deliverables:**
- `pack_share.py`: `create_share`, `update_share_files`, `revoke_share`, `list_shares_for_pack`
- `main.py`: 3 endpoints + 2 Pydantic models
- `plan_limits.py`: `pack_share_limit_monthly` + `check_pack_share_create_allowed`

**Implementation:**
1. `pack_share.create_share(db, user, pack_id, include_files)` — idempotent (ถ้ามี active share ของ pack นี้ → return เดิม)
2. `pack_share.update_share_files(db, user, share_id, include_files)` — toggle
3. `pack_share.revoke_share(db, user, share_id)` — set revoked_at
4. main.py: 3 endpoints (POST /share, PATCH /shares/{id}, DELETE /shares/{id})
5. main.py: 2 Pydantic — `ShareCreateRequest`, `ShareUpdateRequest`

**Playwright verification (M2 — uses curl/fetch via TestClient — no UI yet):**
- M2.1: Create share → 200 + URL returned
- M2.2: Create share again on same pack → idempotent (returns same share_id)
- M2.3: PATCH toggle include_files → updated
- M2.4: DELETE revoke → 200 + revoked_at set
- M2.5: Create share on locked pack → 400 PACK_LOCKED
- M2.6: Free user 6th share → 403 PACK_SHARE_QUOTA_REACHED
- M2.7: User B revoke User A's share → 404 SHARE_NOT_FOUND (steal guard)

**Pass criteria:** 7/7 backend endpoint tests pass

---

### Milestone 3 — Backend Preview + Claim Endpoints (~3 ชม.)

**Deliverables:**
- `pack_share.py`: `get_preview(db, token)`, `claim_to_workspace(db, current_user, token)`
- `main.py`: GET /api/shared/pack/{token} (no auth) + POST /claim + GET /p/{token} HTML route
- `signed_urls.py` integration: generate download URLs for files when include_files=true

**Implementation:**
1. `get_preview(db, token)`:
   - verify_share_token → share_id
   - Lookup share → check revoked_at IS NULL → 403 SHARE_REVOKED
   - Lookup pack → ถ้าไม่มี → 404 PACK_DELETED
   - Atomic increment view_count
   - Build response (mask owner email, generate file URLs ถ้า include_files)
2. `claim_to_workspace(db, current_user, token)`:
   - verify + lookup
   - Pre-check pack quota + storage (ถ้ารวม include_files)
   - Create new ContextPack with created_via="shared_clone"
   - Copy files (ถ้า include_files)
   - Atomic increment clone_count
3. main.py:
   - GET /api/shared/pack/{token} (no Depends auth)
   - POST /api/shared/pack/{token}/claim (Depends get_current_user)
   - GET /p/{token} → return shared_pack.html

**Playwright verification (M3.spec.js — backend only):**
- M3.1: Preview valid token → 200 + content
- M3.2: Preview revoked → 403
- M3.3: Preview pack deleted → 404
- M3.4: View count increment ทุก call (concurrent x3 → count=3)
- M3.5: include_files=true → response มี download_url with signed token
- M3.6: include_files=false → no files array
- M3.7: Claim valid → new pack ใน workspace recipient
- M3.8: Claim w/o auth → 401
- M3.9: Claim w/ pack quota เต็ม → 403
- M3.10: Cloned pack: source_file_ids=[] (privacy)
- M3.11: Cloned pack: created_via="shared_clone"
- M3.12: Owner claim ของตัวเอง → success (use case: backup)

**Pass criteria:** 12/12 backend tests pass

---

### Milestone 4 — Sender Frontend (Pack Card 📤 + Bar) (~3 ชม.)

**Deliverables:**
- app.html: ปุ่ม 📤 + bar template
- app.js: 6 functions + clipboard auto-copy + i18n
- styles.css: `.pack-share-bar` + animation

**Implementation:**
1. app.html — เพิ่มใน pack card actions:
   ```html
   <button onclick="sharePack('${p.id}')" title="Share">📤</button>
   ```
   + bar template (hidden by default, append after card)

2. app.js:
   - `sharePack(packId)` — POST /share → auto-copy URL → show bar + toast
   - `togglePackFiles(shareId, checkbox)` — show confirm if include=true → PATCH → toast + auto-copy new URL
   - `copyShareLink(shareId)` — clipboard write + toast
   - `revokePackShare(shareId)` — DELETE + close bar + reset 📤 button + toast
   - `closePackShareBar(packId)` — hide bar (ลิงก์ยังใช้ได้)
   - `_renderShareBar(pack, share)` — render bar HTML

3. styles.css:
   - `.pack-share-bar` (slide-down animation, padding 12px 16px)
   - `.pack-share-bar.hidden { display: none }`
   - `.pack-share-link` (mono font, ellipsis)
   - `.pack-share-stats` (small, secondary text)

**Playwright verification (M4 sender.spec.js):**
- F-S-1: เห็นปุ่ม 📤 บน pack card
- F-S-2: กด 📤 → bar เด้ง + ลิงก์อยู่ใน clipboard (verify via `navigator.clipboard.readText()`)
- F-S-3: Bar แสดง URL + view count + clone count
- F-S-4: ติ๊ก include_files → confirm dialog เด้ง
- F-S-5: ใน confirm dialog กด "ใช่" → toast + URL copied อีกครั้ง
- F-S-6: ใน confirm dialog กด "ยกเลิก" → checkbox กลับเป็น unchecked
- F-S-7: ติ๊ก include_files แล้วยกออก → toast "เป็นสรุปอย่างเดียว" (no confirm needed for OFF)
- F-S-8: กดปุ่ม [📋 คัดลอก] → clipboard updated + toast
- F-S-9: กด [🚫 ยกเลิก] → bar หาย + ปุ่ม 📤 กลับเป็นปกติ
- F-S-10: หลัง revoke → กด 📤 อีกครั้ง → ลิงก์ใหม่ (different share_id)
- F-S-11: Pack ที่ locked → ปุ่ม 📤 disabled + tooltip "Pack ล็อคแล้วแชร์ไม่ได้"
- F-S-12: Mobile (375px) — bar responsive + button accessible

**Pass criteria:** 12/12 sender UI tests pass บน real Chromium

---

### Milestone 5 — Recipient Frontend (`/p/{token}` page) (~3 ชม.)

**Deliverables:**
- shared_pack.html (NEW) — standalone preview page
- shared_pack.js (NEW) — render + claim flow
- shared_pack.css (NEW) — responsive styling

**Implementation:**
1. shared_pack.html:
   - `<link href="/legacy/shared_pack.css">`
   - 4 main divs: `#loading`, `#error`, `#preview`, `#revoked`
   - Logo + branding minimal
   - `<script src="/legacy/shared_pack.js">`

2. shared_pack.js:
   - On load: extract token from URL (`/p/{token}`)
   - GET `/api/shared/pack/{token}` (no auth header — explicit)
   - Render based on response:
     - 200 → `_renderPreview(data)` — mask owner email + summary short + expand button + files list
     - 403 SHARE_REVOKED → `_showRevoked()`
     - 404 → `_showError("ลิงก์ไม่มีอยู่หรือ pack ถูกลบ")`
   - `claim()` — check localStorage.pdb_token:
     - มี token → POST `/claim` → toast + redirect /app#pack/{new_id}
     - ไม่มี → redirect `/?return=/p/{token}&action=claim` (landing.js handle action=claim post-login)
   - `expandSummary()` — toggle summary_short ↔ summary_full
   - `closeBrowser()` — `window.close()` หรือ redirect /

3. landing.js — handle `?action=claim&return=/p/{token}` post-login → auto-redirect back

4. shared_pack.css:
   - Mobile-first design (96vw default)
   - Card layout — center, max 720px
   - Sticky CTA button at bottom on mobile

**Playwright verification (M5 recipient.spec.js):**
- F-R-1: Open `/p/{token}` (no login) → preview shown
- F-R-2: Preview แสดงชื่อ pack, masked owner (te****@x.com), intent, scope
- F-R-3: Summary แสดงย่อก่อน (300 chars) + ปุ่ม "ดูเต็ม"
- F-R-4: กด "ดูเต็ม" → expand แสดงทั้งหมด
- F-R-5: include_files=true → ดู files list + download URL clickable
- F-R-6: include_files=false → ซ่อน files section
- F-R-7: Open revoked share → แสดง error "ลิงก์ถูกยกเลิก"
- F-R-8: Open invalid token → แสดง 404 page
- F-R-9: กด "เก็บ" + ยังไม่ login → redirect ไป `/?return=...`
- F-R-10: หลัง register/login → กลับมาที่ `/p/{token}` → claim สำเร็จ → redirect /app
- F-R-11: กด "เก็บ" + login แล้ว → POST claim → toast success → redirect /app
- F-R-12: กด "ปิดหน้านี้" → window.close หรือ redirect /
- F-R-13: View count เพิ่มขึ้นทุกครั้งที่เปิด (verify via 2 visits)
- F-R-14: Mobile (375px) responsive — card ขยายเต็ม 96vw, sticky CTA

**Pass criteria:** 14/14 recipient UI tests pass

---

### Milestone 6 — End-to-End Integration + Cross-User (~2 ชม.)

**Deliverables:** Integration spec ที่ test ครบ flow sender → recipient → claim

**Playwright verification (M6 integration.spec.js):**
- E2E-1: User A สร้าง share → User B เปิดลิงก์ → preview → claim → User B มี cloned pack
- E2E-2: User A revoke ระหว่าง User B preview อยู่ → reload → revoked page
- E2E-3: Owner ลบ pack หลัง share → recipient preview → 404 PACK_DELETED แต่ pack เก่าที่ claim ไปแล้วยังอยู่
- E2E-4: User A include_files=true → User B claim → ไฟล์อยู่ใน workspace User B + source_file_ids ของ pack ใหม่ != ของ User A (privacy preserved)
- E2E-5: Race: 2 users claim share เดียวกันพร้อมกัน → ทั้งคู่ได้ pack คนละชุด + clone_count = 2
- E2E-6: User B claim → User B share ต่อให้ User C → User C claim → chain works
- E2E-7: Free user A → 5 shares → ครบ → กด 6 → 403 quota reached
- E2E-8: User A revoke share #3 → ยังเหลือ 4 active → กด share ใหม่ → success (ไม่นับ revoked เก่าซ้ำ — wait need decide rule)

**Decision for E2E-8:** revoked share **นับเข้า quota เดือนนี้** เพื่อกัน abuse (revoke→create loop)

**Pass criteria:** 8/8 E2E tests pass

---

### Milestone 7 — Polish + Comprehensive Tests + Version Bump (~2 ชม.)

**Deliverables:**
- `scripts/share_pack_smoke.py` (25 cases)
- `tests/test_share_pack_v9_3.py` (35 cases pytest)
- Final regression: v9.0.1 + v9.2.0 + v9.2.2 ยังผ่าน
- APP_VERSION 9.2.2 → 9.3.0
- Memory updates: pipeline-state, last-session, plan archive

**Playwright (M7 polish.spec.js):**
- M7.1: Version label app.html shows v9.3.0
- M7.2: Pack card with active share shows 🔗 badge
- M7.3: A11y: ปุ่ม 📤 มี aria-label "Share pack"
- M7.4: A11y: dialog confirm มี role="dialog" + aria-modal="true"
- M7.5: Keyboard nav: Tab ผ่าน bar elements ครบ + Enter activate buttons
- M7.6: Toast messages — TH/EN follow getLang()

**Pass criteria:** 6/6 + total regression

---

## 🧪 Comprehensive Test Suite

### Layer 1: Smoke (`scripts/share_pack_smoke.py`) — 25 cases

**Group A: Sender backend (5)**
- T-A1 create_share new → returns share + URL
- T-A2 create_share existing → idempotent same share_id
- T-A3 update_share_files toggle → include_files updated
- T-A4 revoke_share → revoked_at set
- T-A5 list_shares_for_pack → all shares of user's pack

**Group B: Locked + quota (4)**
- T-B1 create on locked pack → 400 PACK_LOCKED
- T-B2 free user 6th share → 403 quota
- T-B3 starter user 51st → 403
- T-B4 admin → unlimited

**Group C: Preview (5)**
- T-C1 valid token → content + view_count++
- T-C2 revoked → 403
- T-C3 pack deleted → 404
- T-C4 invalid token → 401
- T-C5 include_files=true → file URLs in response

**Group D: Claim (6)**
- T-D1 valid claim → new pack of recipient
- T-D2 source_file_ids=[] (privacy)
- T-D3 created_via="shared_clone"
- T-D4 intent has note "(เก็บจาก ... เมื่อ ...)"
- T-D5 clone_count++
- T-D6 owner self-claim → success (backup use case)

**Group E: Edge cases (5)**
- T-E1 cross-user revoke → 404 SHARE_NOT_FOUND
- T-E2 cross-user update → 404
- T-E3 race: 2 concurrent views → count = 2 (atomic)
- T-E4 race: 2 concurrent claims → both succeed + count = 2
- T-E5 owner pack quota เต็ม → ยังสร้าง share ได้ (quota เป็นของแยก)

### Layer 2: Pytest (`tests/test_share_pack_v9_3.py`) — 35 cases

**Group F: API contract validation (8)**
- F1-F8: Pydantic boundaries, required fields, type validation

**Group G: Auth (5)**
- G1: no JWT on /share → 401
- G2: invalid JWT → 401
- G3: no JWT on /preview → 200 OK (no auth required)
- G4: no JWT on /claim → 401
- G5: no JWT on /shares (revoke) → 401

**Group H: Files attached flow (6)**
- H1: include_files=true + 5 files → all download URLs work
- H2: download URL TTL 1 hour
- H3: download URL after revoke → 403
- H4: claim with include_files=true → files copied to recipient workspace
- H5: storage quota check before file copy
- H6: BYOS user files → server proxy via signed_urls

**Group I: Privacy + masking (4)**
- I1: owner email masked te****@x.com
- I2: owner_user_id NOT in preview response
- I3: cloned pack source_file_ids != owner's
- I4: cloned pack source_cluster_ids = [] (no leak)

**Group J: TTL + revoke + GC (4)**
- J1: revoked share preview → 403
- J2: revoke twice → idempotent
- J3: revoked share counted in monthly quota (anti-abuse)
- J4: deleted pack → preview 404 but cloned packs still alive

**Group K: API integration (8)**
- K1-K8: end-to-end via TestClient — create→preview→claim→list→update→revoke→repreview→reclaim

### Layer 3: Playwright sender — `tests/e2e-ui/v9.3.0-share-pack-sender.spec.js` (12 cases)

ดู Milestone 4 verification ด้านบน (F-S-1 ถึง F-S-12)

### Layer 4: Playwright recipient — `tests/e2e-ui/v9.3.0-share-pack-recipient.spec.js` (14 cases)

ดู Milestone 5 verification ด้านบน (F-R-1 ถึง F-R-14)

### Layer 5: Playwright integration — embedded ใน sender/recipient specs

ดู Milestone 6 verification (E2E-1 ถึง E2E-8)

### Total: **25 + 35 + 12 + 14 + 8 = 94 cases**

---

## ✅ Done Criteria

- [ ] PackShare table created via init_db
- [ ] 5 endpoints + 1 HTML route ครบ
- [ ] pack_share.py module ครบ functions
- [ ] Frontend sender: ปุ่ม 📤 + bar + toggle + revoke + auto-copy clipboard
- [ ] Frontend recipient: standalone shared_pack.html + claim flow + register/login redirect
- [ ] Plan limits + monthly quota enforcement
- [ ] Privacy: locked guard + masked email + privacy-safe clone (source_file_ids=[])
- [ ] All 7 milestones verified ผ่าน Playwright
- [ ] Total 94 tests pass:
  - [ ] Smoke 25/25
  - [ ] Pytest 35/35
  - [ ] Playwright sender 12/12
  - [ ] Playwright recipient 14/14
  - [ ] Playwright integration 8/8
- [ ] Regression v9.0.1 + v9.2.0 + v9.2.2 ผ่าน
- [ ] APP_VERSION 9.2.2 → 9.3.0
- [ ] Memory updates: pipeline-state, last-session, plan archive
- [ ] Commits แยก 7 logical (1 ต่อ milestone):
  1. `feat(db): pack_shares table + token signing [v9.3.0 M1]`
  2. `feat(api): create/update/revoke share endpoints + plan limits [v9.3.0 M2]`
  3. `feat(api): preview + claim endpoints + signed URLs integration [v9.3.0 M3]`
  4. `feat(frontend): sender pack card 📤 button + share bar + auto-copy [v9.3.0 M4]`
  5. `feat(frontend): recipient /p/{token} preview page + claim flow [v9.3.0 M5]`
  6. `test(e2e): integration + cross-user + race conditions [v9.3.0 M6]`
  7. `test(playwright): polish + a11y + 94 cases comprehensive + bump v9.3.0 [M7]`

---

## ⚠️ Risks & Open Questions

### Risks (with mitigations)
1. **R1 Link leak** — ใครมีลิงก์ก็ดูได้ → revoke ได้ทุกเมื่อ + ลบ pack = 404
2. **R2 Clipboard API** — บาง browser/HTTPS only → fallback `document.execCommand('copy')` + manual copy fallback
3. **R3 Storage abuse via claim** — recipient claim ไฟล์ใหญ่ × N → ตรวจ storage quota ก่อน + 403 ถ้าเกิน
4. **R4 Race on view_count** — atomic UPDATE SQL (`SET view_count = view_count + 1`)
5. **R5 BYOS file proxy** — Drive private → reuse signed_urls.py pattern + server fetches Drive
6. **R6 Cross-origin claim** — recipient user ที่ login ใน different tab → token still valid (JWT stateless)
7. **R7 Pack regenerate during preview** — preview shows current pack content (not snapshot) — feature, not bug. UI shows "Last updated"
8. **R8 Revoke abuse** — revoked count in quota (anti-loop)

### Open Questions (Q1-Q10 — มี default ทุกข้อ)

| Q | Question | Default |
|---|---|---|
| Q1 | Cloned pack title prefix? | ใช้ของเดิม + intent มี note "(เก็บจาก {owner} เมื่อ ...)" |
| Q2 | include_files=true claim → copy files หรือ link? | **Copy เข้า recipient's storage** (consume quota) |
| Q3 | Mask email format? | `te****@x.com` (2 chars + 4 stars) |
| Q4 | Preview summary cutoff? | **300 chars** + ปุ่ม "ดูเต็ม" |
| Q5 | Free monthly quota? | **5 shares** |
| Q6 | Owner self-claim allowed? | **Yes** (use case: backup) |
| Q7 | Revoked share counts in monthly quota? | **Yes** (anti-abuse loop) |
| Q8 | Welcome email after register-via-claim? | **No** (use existing register flow) |
| Q9 | Recipient page domain? | `personaldatabank.fly.dev/p/{token}` (same domain) |
| Q10 | Toast for "URL copied"? | TH "คัดลอกลิงก์แล้ว — ส่งให้เพื่อนได้เลย" / EN "Link copied — paste anywhere" |

---

## 📝 Notes for เขียว

### Critical gotchas (ห้ามพลาด)

1. **Idempotent /share** — ก่อน create ตรวจ active share (`revoked_at IS NULL`) → return เดิม + `is_new=false` → กัน count quota เกิน
2. **JWT no exp** — token signed without expiration → revoke ใช้ DB row check ทุก request
3. **Clipboard API** — ต้องเรียกจาก user gesture (click handler ตรงๆ) ไม่ใช่ async callback. ใช้ `try/catch + fallback execCommand`
4. **Recipient page no auth** — ใช้ static HTML + JS fetch ตรง — ไม่ใช้ `Depends(get_current_user)` ที่ /preview
5. **Owner email mask** — ที่ `_serialize_share_preview` (ไม่ใช่ที่ frontend) — กัน leak via DevTools
6. **File copy on claim** — ใช้ `shutil.copy` ไป recipient's UPLOAD_DIR + create File row ใหม่. Storage quota ตรวจก่อน
7. **Cloned pack source_file_ids** — ถ้า include_files=true → set เป็น new file IDs; ถ้า false → set = []
8. **Atomic counters** — ใช้ `UPDATE pack_shares SET view_count = view_count + 1 WHERE id = ?` ไม่ใช่ Python read-modify-write
9. **No TTL means nothing expires** — design choice, not bug. ใช้ revoke เป็น only deactivation
10. **Confirm dialog ตอนติ๊ก include_files=true** — เพื่อ privacy guard. ถ้าติ๊ก OFF ไม่ต้อง confirm

### Reuse patterns
- ดู [backend/signed_urls.py](../../backend/signed_urls.py) สำหรับ JWT scoped token (`pack_share` scope ใหม่)
- ดู [backend/admin.py](../../backend/admin.py) สำหรับ module + endpoint structure
- ดู [legacy-frontend/admin.html](../../legacy-frontend/admin.html) สำหรับ standalone page pattern
- ดู [scripts/ai_pack_builder_smoke.py](../../scripts/ai_pack_builder_smoke.py) เป็น smoke test template
- ดู [tests/test_ai_pack_builder_v9_2.py](../../tests/test_ai_pack_builder_v9_2.py) เป็น pytest comprehensive template
- ดู [tests/e2e-ui/v9.2.0-ai-pack-builder.spec.js](../../tests/e2e-ui/v9.2.0-ai-pack-builder.spec.js) เป็น Playwright pattern

### Out of scope (do NOT implement in v9.3.0)
- ❌ Email whitelist (เลื่อน v9.4.0+ — ถ้ามี demand)
- ❌ TTL slider (revoke-only design)
- ❌ Permission tier (clone-only)
- ❌ Audit log per access (use view_count + clone_count denormalized)
- ❌ MCP create_share tool
- ❌ Email notification recipient
- ❌ Subscribe / live update / co-edit

ถ้าเจอประเด็นใหม่ที่ต้องตัดสิน → แจ้งผ่าน [inbox/for-แดง.md](../communication/inbox/for-แดง.md) ก่อนตัดสินใจ

---

## 🔍 Plan Review Findings & Fixes (2026-05-08)

แดงตรวจ plan vs actual code — พบประเด็นต้อง clarify ก่อน build:

### 🔴 Critical issues (ต้องแก้ก่อน build)

#### F1. signed_urls token signing — ใช้ owner's user_id (ไม่ใช่ recipient)
**Issue:** `signed_urls.sign_download_token(file_id, user_id, ttl)` ต้องการ `user_id` = เจ้าของไฟล์ (ใช้ verify ที่ /d/{token})
**Fix:** ใน `get_preview()` ตอน gen download URLs ใช้ `share.owner_user_id` (sender's id) ไม่ใช่ recipient — เพราะไฟล์เป็นของ owner. Recipient แค่ "ยืม" ลิงก์ดู

#### F2. TTL inconsistency — share link ไม่มี TTL แต่ download URL = 1 hour
**Issue:** ถ้า recipient เปิด preview แล้ว 2 ชม. ต่อมากดดาวน์โหลด → URL หมดอายุ
**Fix strategy:**
- Frontend: ทุกครั้งที่ user คลิกปุ่ม download ใน recipient page → re-fetch /preview เพื่อได้ fresh URLs (ใช้ background AJAX) — transparent กับ user
- Alternative: extend signed_urls TTL_MAX_SECONDS เป็น 86400 (1 day) สำหรับ pack share use case → เพิ่ม `scope="pack_share_file"` ใหม่
- **Decision: Option A (re-fetch)** — เก็บ TTL เดิม, frontend จัดการ refresh

#### F3. Privacy guard vs simplicity — confirm dialog ขัดกับ "1 คลิก"
**Issue:** Plan เก่าบอก "ติ๊ก include_files=true → confirm dialog เด้ง" — แต่ user vision คือ "ง่าย ไม่ติดขัด"
**Fix:** ตัด confirm dialog ออก. แทนด้วย **inline warning text** ใต้ checkbox:
```
☑ + แนบไฟล์ทั้งหมด (5 ไฟล์ · 12 MB)
   ⚠ ใครเปิดลิงก์จะดาวน์โหลดไฟล์เหล่านี้ได้
```
การติ๊ก = consent ในตัว — ไม่ต้องคลิกซ้ำ

### 🟡 Medium issues (clarify ใน plan)

#### F4. BYOS file proxy — reuse existing /d/{token} pattern
**Issue:** Plan บอก "Drive private → server proxy" ไม่ชัด
**Fix:** ใน `get_preview()` gen download URLs ผ่าน `signed_urls.sign_download_token` → URL = `https://.../d/{token}`. ที่ /d/{token} endpoint (existing v7.6.0) มี logic BYOS-aware อยู่แล้วผ่าน storage_router → เรา reuse 100% ไม่ต้องเขียน proxy ใหม่

#### F5. File copy on claim — skip BYOS files ใน v9.3.0
**Issue:** Owner เก็บไฟล์ใน Google Drive (BYOS) → recipient claim → copy ทำยังไง?
**Fix v9.3.0:** เก็บแบบ pragmatic:
- ถ้า file.storage_source != "local" → skip copy + เพิ่มใน clone pack note: "(ไฟล์ {N} อันใน BYOS ของเจ้าของ ไม่ได้ copy)"
- เลื่อน BYOS-to-BYOS copy ไป v9.4.0
- include_files=true จะ copy เฉพาะ local files

#### F6. Vector search re-indexing for cloned pack
**Issue:** Plan ไม่ได้ระบุ
**Fix:** ใน `claim_to_workspace` หลัง create_pack สำเร็จ → reuse pattern จาก v9.0.1: `vector_search.index_file(file_id=f"pack-{new_pack.id}", ...)` (create_pack ทำให้อยู่แล้ว — แค่ verify)

#### F7. i18n keys explicit list
**Add ใน plan:**
```
share.button.tooltip          : "Share pack" / "แชร์ Pack"
share.toast.copied            : "Link copied — paste anywhere" / "คัดลอกลิงก์แล้ว — ส่งให้เพื่อนได้เลย"
share.bar.linkLabel           : "Share Link"
share.bar.copyButton          : "Copy" / "คัดลอก"
share.bar.includeFiles        : "+ Attach all files" / "+ แนบไฟล์ทั้งหมด"
share.bar.filesWarning        : "⚠ Anyone with link can download" / "⚠ ใครเปิดลิงก์ดาวน์โหลดได้"
share.bar.statsViews          : "{n} views" / "{n} views"
share.bar.statsClones         : "{n} clones" / "{n} clones"
share.bar.revoke              : "Revoke link" / "ยกเลิกลิงก์"
share.bar.close               : "Close" / "ปิด"
share.toast.includeOn         : "Link now includes {n} files" / "ลิงก์มีไฟล์แนบ {n} ไฟล์แล้ว"
share.toast.includeOff        : "Link is summary-only" / "ลิงก์เป็นสรุปอย่างเดียวแล้ว"
share.toast.revoked           : "Link revoked" / "ยกเลิกลิงก์แล้ว"
share.button.lockedTooltip    : "Locked packs cannot be shared" / "Pack ที่ล็อคแชร์ไม่ได้"
```
รวม **14 keys** (ตามที่ plan บอก)

#### F8. Storage quota pre-check formula (สำหรับ claim with files)
**Add ใน plan:**
```python
# ใน claim_to_workspace — ก่อน copy files
if include_files and source_files:
    total_size_mb = sum(f.raw_path size) for local files only
    available_mb = limits["storage_limit_mb"] - current_usage_mb
    if total_size_mb > available_mb:
        raise StorageQuotaError(needed=total_size_mb, available=available_mb)
```

#### F9. landing.js `?action=claim&return=...` handler
**Add ใน plan implementation steps (Milestone 5):**
```javascript
// landing.js — post-login redirect handler
const urlParams = new URLSearchParams(window.location.search);
const returnPath = urlParams.get('return');
const action = urlParams.get('action');
if (returnPath && returnPath.startsWith('/p/')) {
    // หลัง login สำเร็จ → redirect กลับ recipient page
    window.location.href = returnPath + (action === 'claim' ? '?autoclaim=1' : '');
}
```
+ shared_pack.js handle `?autoclaim=1` → call /claim ทันที post-login

#### F10. Playwright clipboard permission
**Add ใน gotchas:**
```javascript
// ใน Playwright spec — ก่อน sharePack test
await context.grantPermissions(['clipboard-read', 'clipboard-write']);
```
ถ้าไม่ grant → `navigator.clipboard.readText()` reject → F-S-2 fail

#### F11. F-R-13 view count test — sequential not concurrent
**Fix:** เปลี่ยนจาก "concurrent visits" → "sequential visits ×3 → check count = 3" (ง่าย deterministic)

### Summary of fixes

| # | Severity | Section affected | Fix applied |
|---|---|---|---|
| F1 | 🔴 | get_preview signing | use share.owner_user_id |
| F2 | 🔴 | TTL strategy | re-fetch on download click |
| F3 | 🔴 | Privacy UX | inline warning, no confirm |
| F4 | 🟡 | BYOS proxy | reuse /d/{token} existing |
| F5 | 🟡 | File copy on claim | skip BYOS in v9.3.0 |
| F6 | 🟡 | Vector index | already in create_pack |
| F7 | 🟡 | i18n keys | 14 keys listed |
| F8 | 🟡 | Storage quota | formula specified |
| F9 | 🟡 | Login redirect | landing.js handler added |
| F10 | 🟡 | Playwright | grantPermissions added |
| F11 | 🟡 | F-R-13 test | sequential x3 |

**ผลกระทบต่อ effort:** 0 — ทุก fix เป็นการ clarify spec ที่มีอยู่ ไม่เพิ่มงานใหม่

**ผลกระทบต่อ tests:** ลดเหลือ 92 cases (ตัด confirm dialog tests F-S-4, F-S-5, F-S-6 → กลายเป็น "warning text visible" 1 test แทน)

---

---

## 🛡️ Proactive Cascade Risk Analysis (2026-05-08)

> User asked: "ถ้าอันนี้พังจะกระทบส่วนอื่นไหม — เราทำเชิงรุก ไม่ใช่รอแก้ทีหลัง"
>
> ผมตรวจทุก system ที่ v9.3.0 touch + verify guard + plan rollback strategy

### 🎯 11 systems ที่ touch + cascade risk

| # | System | Action | Cascade risk | Guard / Mitigation | Verified |
|---|---|---|---|---|---|
| 1 | `pack_shares` table | NEW | 🟢 ไม่มี (table ใหม่ ไม่กระทบ existing) | `Base.metadata.create_all` idempotent + non-destructive | ✅ |
| 2 | `files` table | WRITE (claim copies) | 🔴 **HIGH** — malformed File row → break /api/files listing → ALL users | Atomic transaction + try/except wrap + rollback on partial failure | 🚧 |
| 3 | `context_packs` table | WRITE (clone) | 🟡 — duplicate id หรือ FK violation | Use `gen_id()` (existing pattern) + FK to recipient.id | ✅ |
| 4 | `vector_search` index | WRITE (cloned pack) | 🔴 **HIGH** — cross-user index leak | per-user dict already + `index_file(user_id=)` (v9.0.1 pattern) | ✅ verified pattern |
| 5 | `JWT_SECRET_KEY` | REUSE for share token | 🔴 **HIGH** — share token leak → maybe abuse as login token? | Explicit `scope="pack_share"` check at verify; existing scope guards in `signed_urls.SCOPE_DOWNLOAD` pattern | ✅ verified |
| 6 | `plan_limits` add key | additive | 🟢 LOW — verified no `limits.items()` iteration anywhere | grep ผ่าน — ทุก consumer ใช้ specific key (`limits['file_limit']`) | ✅ verified |
| 7 | `UsageLog.action` new values | additive | 🟢 LOW | grep ผ่าน — consumers check specific values only (`== "ai_summary"`) | ✅ verified |
| 8 | `_serialize_pack` add fields | additive | 🟢 LOW — old MCP/UI clients ignore unknown fields | additive only, no field removal | ✅ |
| 9 | `landing.js` modify | post-login redirect | 🟡 — buggy redirect → user ปกติ login ไม่ได้ | guard: only trigger if `return.startsWith('/p/')` | 🚧 |
| 10 | `/d/{token}` endpoint | REUSE for downloads | 🟡 — existing /d/ logic break ถ้า token format different | use `signed_urls.sign_download_token` exact format — no changes to endpoint | ✅ |
| 11 | `register/login` API | REUSE for recipient register | 🟢 LOW — auth flow unchanged | Recipient ใช้ existing `doRegister()` — no branch | ✅ |

**Legend:** ✅ verified · 🚧 to be implemented per plan · ⚠️ open

### 🚨 Top-3 Cascade Risks (deep-dive)

#### Risk 1: File copy on claim → break `/api/files` listing
**Failure mode:**
```
recipient claim → loop copy files
  → file 1 ✅ (DB row + raw_path written)
  → file 2 ✅
  → file 3 ❌ (disk full / permission / OOM)
  → DB has 3 File rows but only 2 raw_path exist
  → /api/files listing → 1 row missing raw → 500 error → break ALL recipient's file UI
```

**Guard (เพิ่มใน claim_to_workspace):**
```python
async def claim_to_workspace(db, current_user, token):
    # 1. Pre-check storage quota (ตามที่มี)
    # 2. Pre-check ALL files exist on disk (ก่อน start copy)
    for f in source_files:
        if f.storage_source == "local" and not os.path.exists(f.raw_path):
            raise FileNotFoundError(f"Source file missing: {f.filename}")
    
    # 3. Copy files in transaction-safe order:
    new_file_records = []
    copied_paths = []
    try:
        for f in source_files:
            new_path = ...  # recipient's UPLOAD_DIR
            shutil.copy2(f.raw_path, new_path)  # copy WITH metadata
            copied_paths.append(new_path)
            new_file_record = File(...)
            db.add(new_file_record)
            new_file_records.append(new_file_record)
        # Create pack pointing to new files
        new_pack = await create_pack(...)
        await db.commit()  # ATOMIC: all-or-nothing
    except Exception as e:
        # Rollback: delete copied files + DB rolls back automatically
        for p in copied_paths:
            try: os.remove(p)
            except: pass
        raise
```

#### Risk 2: Vector index cross-user leak
**Failure mode:**
```
recipient.user_id = "user_b"
clone pack → call vector_search.index_file(file_id="pack-{new}", user_id="user_a")  ❌
→ pack ของ user_b เข้า user_a's index
→ user_a search → เห็น pack ที่ไม่ใช่ของตัวเอง
```

**Guard:** ใน `claim_to_workspace`:
```python
# v9.3.0 — explicitly use recipient.id (not owner)
vector_search.index_file(
    file_id=f"pack-{new_pack['id']}",
    user_id=current_user.id,  # ⚠️ recipient, NOT share.owner_user_id
    ...
)
```

`create_pack()` ทำให้อยู่แล้ว (ใช้ `user_id` arg ที่ส่งเข้าไป — pattern verified ใน v9.0.1)

#### Risk 3: JWT scope confusion
**Failure mode:**
```
attacker: gets pack_share token
→ tries /api/auth/me with Bearer pack_share_token
→ if /api/auth/me ไม่ check scope → leak access
```

**Guard:**
- `decode_token` ใน auth.py ไม่ check scope (current behavior)
- BUT `auth.get_current_user` ใช้ payload's `sub` (user_id) field
- pack_share token payload = `{share_id, scope, iat}` — **ไม่มี `sub` field**
- → `get_current_user` จะ raise 401 because `sub` missing
- ✅ **Implicit guard ผ่าน payload structure differs**

แต่เพื่อ defense-in-depth, ใน `verify_share_token` ตรวจ `scope == "pack_share"` explicit (ตามที่ plan บอก) ✅

---

## 🔧 Production Readiness Checklist

### Pre-deploy gates (ต้องทำก่อน push origin)

- [ ] **Feature flag** — เพิ่ม env var `ENABLE_PACK_SHARING=true` (default true) — disable instantly ถ้า production พัง
  - Wire ใน main.py ที่ทุก /api/context-packs/share* endpoints → return 503 ถ้า disabled
  - Frontend: ปุ่ม 📤 hidden ถ้า `state.features.pack_sharing === false`
- [ ] **Migration test** — รัน init_db บน production-like DB → verify pack_shares สร้าง + existing data unchanged
- [ ] **Rollback plan documented** — ดู section ด้านล่าง

### Monitoring + observability

- [ ] **Usage tracking** ผ่าน `log_usage`:
  - `"pack_share"` ทุก /share success
  - `"pack_share_view"` ทุก /preview view (volumetric)
  - `"pack_clone"` ทุก /claim success
- [ ] **Admin panel** — แสดง count ใน Dashboard tab (existing pattern):
  - "Active shares: N · Total clones: M · Views today: K"
- [ ] **Error rate alert** — ถ้า /preview 5xx > 5%/hour → log critical

### Rollback Plan

ถ้าหลัง deploy มีปัญหา (production user reports):

#### Level 1: Disable feature flag (instant — no rebuild)
```bash
fly secrets set ENABLE_PACK_SHARING=false
fly machine restart  # ~30s
```
ผลลัพธ์: ปุ่ม 📤 หายจาก UI, /share endpoints return 503, ไม่กระทบ pack อื่นๆ

#### Level 2: Code revert (full rollback)
```bash
git revert <merge-commit>
git push origin master
fly deploy
```
ผลลัพธ์: backend กลับ v9.2.2, pack_shares table ยังอยู่ (ไม่ destructive), cloned packs ของ user ยังอยู่ใน workspace

#### Level 3: Cleanup orphans (เผื่อ Level 2 ไม่พอ)
```python
# scripts/v9_3_cleanup.py
# - Delete pack_shares rows (no relation cascading)
# - cloned packs ของ recipient = ยังอยู่ (เป็น first-class pack ของ user แล้ว)
# - File copies ของ recipient = ยังอยู่ (เป็น first-class file)
```

**Key insight:** v9.3.0 design = **clone-then-disconnect** → ถ้า rollback, recipient's packs/files ยังอยู่กับเขา ไม่หาย ไม่ break ❤️

### Resource impact analysis

| Resource | Before | After (with v9.3.0) | Impact |
|---|---|---|---|
| DB rows | files + packs | + pack_shares (1 per share) | minimal |
| Disk | upload dirs | + cloned files (recipient owns) | up to 2x for sharing pairs |
| LLM cost | summary + clarify + select + distill | **0 ใหม่** (v9.3.0 ไม่ call LLM) | ✅ no impact |
| Bandwidth | uploads + downloads | + share preview + file downloads | moderate increase |
| Memory | TF-IDF index per user | + pack indexes (1 per cloned pack) | minimal |

### Security review (proactive)

- [ ] **No credential leak in shares** — share preview returns owner_email_masked, NOT raw email
- [ ] **No pack content leak via cache** — `view_count++` invalidates cached preview (recipients always see fresh)
- [ ] **No CSRF risk** — POST /share + DELETE /shares require Authorization header (no cookies)
- [ ] **No XSS via title/intent/scope** — frontend uses `escapeHtml()` (existing pattern)
- [ ] **Rate limiting** — share creation = quota-limited (Free 5/mo, Starter 50/mo); preview = unlimited but read-only; claim = recipient's pack quota

### Test coverage gaps to fix in M6 + M7

- [ ] E2E-9 (NEW): Feature flag OFF → /share returns 503 + UI hides button
- [ ] E2E-10 (NEW): Disk full simulation → claim rolls back cleanly (no orphan files)
- [ ] E2E-11 (NEW): Owner deletes account → cascade behavior (pack_shares preserved? cloned packs survive?)

→ **เพิ่มใน Milestone 6 = 11 E2E tests (จาก 8)**
→ **Total tests: 92 → 95 cases**

---

## 📋 Pipeline Next

1. 🔴 **User review plan + findings + cascade analysis** — accept proactive guards
2. 🟢 **เขียว build** — Milestone 1 → 7 (~2.5 วัน + Playwright per milestone + cascade guards in M3 + M5 + M6)
3. 🔵 **ฟ้า review** — verify privacy + 95 tests + cascade guards + commit messages
4. 🔴 **User approve + feature-flag deploy + monitor**

---

## 📊 ความคุ้ม

| Metric | Simple Edition (เดิม) | Detailed Edition (นี้) |
|---|---|---|
| Total tests | 53 | **94** |
| Playwright UI tests | 8 | **34** (sender 12 + recipient 14 + integration 8) |
| Milestones with verification | 0 | **7** |
| Lines of plan | ~400 | ~720 |
| Confidence in ship | กลาง | **สูง** |
| Effort | ~2 วัน | ~2.5 วัน (เพิ่ม 0.5 วันคุ้ม) |

**ตรง vibe ที่ user ขอ:**
- ✅ "ละเอียดจริงๆ" — มี milestone, test plan, UI flow, edge cases ครบ
- ✅ "ทุก milestone มีเทส" — 7 milestones × Playwright per milestone
- ✅ "เทสหน้า UI จริง ทั้งผู้รับและผู้ส่ง ด้วย Playwright" — 34 Playwright cases (sender 12 + recipient 14 + integration 8)
