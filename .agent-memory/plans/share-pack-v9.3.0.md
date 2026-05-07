# Plan: Share Context Pack — v9.3.0

> **Status:** `plan_pending_approval`
> **Author:** 🔴 แดง (Daeng) — 2026-05-07
> **Foundation:** v9.2.1 master (after AI Pack Builder + Mobile Fixes ship)
> **Estimated effort:** เขียว ~3 วัน + ฟ้า ~1 วัน
> **Risk:** 🟠 Medium-High — privacy-sensitive feature ต้องมี explicit consent + revoke ได้
>
> **User vision (verbatim 2026-05-07):**
> "อยากให้มันสามารถแชร์ context pack กับคนอื่นได้ — ฟีเจอร์นี้ต้องคิดทบทวนดีๆ"

---

## 🎯 Goal & Context

### Why
Pack ที่ user สร้าง = "knowledge cache ที่กลั่นจากข้อมูลส่วนตัว" — ปัจจุบันใช้ส่วนตัวอย่างเดียว ไม่มีวิธีส่งให้คนอื่น (เพื่อนร่วมงาน, นักศึกษา, ทีม) ทำให้:
1. **Lock-in to single user** — pack มีประโยชน์น้อย ถ้าใช้คนเดียว
2. **Manual workaround** — user ทำ "ส่งออกเป็น text + paste ใน chat" → ไม่ได้ context structure ของ pack
3. **Use cases ที่หายไป:** team work (founder + cofounder), education (อาจารย์ → นักศึกษา), public knowledge sharing

### Goals (Archetype B — Balanced per user 2026-05-07)
1. **Owner สร้าง share link** ได้ — กำหนด audience (email whitelist) + permission (view/clone) + TTL
2. **Recipient view** — เข้าได้ผ่าน link, view summary + intent + scope + ชื่อไฟล์ source (ไม่เห็น content ไฟล์)
3. **Recipient clone** — copy pack เป็นของตัวเองใน workspace ตัวเอง (ต้อง login PDB)
4. **Privacy by default** — confirmation modal ก่อน share + แสดง source files list + revoke ได้ทุกเมื่อ + audit log

### Non-goals (เลื่อน v9.4.0+)
- ❌ Subscribe (auto-sync) — ผู้รับ get update เมื่อ owner regenerate (เลื่อน)
- ❌ Source file content sharing (privacy nightmare — แชร์เนื้อหาไฟล์)
- ❌ Password-protected link
- ❌ Public link (anyone-with-link)
- ❌ Pack collaboration (multi-owner edit)
- ❌ MCP tool รองรับ create share link (เลื่อน v9.4.0)
- ❌ Email notification ผู้รับเมื่อ share สร้าง (เลื่อน — ใช้ Resend)

### Design decisions (per user 2026-05-07)
- **Q1 Audience:** B (Email whitelist) + C (require PDB login) — recipient ต้อง login + email match list
- **Q2 Permission:** B (View + Clone) — เห็นเนื้อหา + กดสร้างสำเนาในตัวเองได้
- **Q3 Content:** B (summary + intent + scope + ชื่อไฟล์ + type — ไม่รวม content ไฟล์)
- **Q4 Lifecycle:** B (TTL 30 วัน default + revoke ได้ทุกเมื่อ, ไม่มี password)
- **Q5 Plan gate:** C (Quota — Free 1/เดือน, Starter 50/เดือน, Admin unlimited)
- **Q6 Use case:** work team + personal backup
- **Q7 Recipient view URL:** หน้าใหม่ `/shared/pack/{token}` — แยกจาก `/app` กัน auth state hijack
- **Q8 Tracking:** เก็บ access count + first/last access + recipient_user_id ใน access log
- **Q9 ลบ pack ต้นทาง:** share link → 404 (lazy — token ยังอยู่แต่ verify จะ fail)
- **Q10 MCP integration:** ไม่ทำใน v9.3 → v9.4

### Privacy guards (non-negotiable)
1. **Default = private** — share = explicit action ไม่มี auto-share
2. **Confirmation modal** — แสดง list ไฟล์ source + checkbox "ยืนยันว่าเข้าใจว่าข้อมูล (สรุป + ชื่อไฟล์) จะถูก share"
3. **Revoke ได้ทุกเมื่อ** — UI ปุ่ม "ยกเลิกลิงก์" + audit แสดงประวัติ access
4. **TTL ไม่เกิน 90 วัน** — กัน orphan link ที่ลืมไว้
5. **Recipient ต้อง login** — ไม่มี anonymous access (กัน DDoS + accountability)

---

## 📁 Files to Create / Modify

| File | Action | Reason |
|------|--------|--------|
| `backend/database.py` | **modify** | เพิ่ม `PackShare` table + `PackShareAccess` table + idempotent migration |
| `backend/pack_share.py` | **create** (~280 lines) | Core module: create_share, verify_share_token, list_shares, revoke_share, log_access, clone_shared_pack |
| `backend/main.py` | **modify** | 5 Pydantic models + 6 endpoints (create/list/revoke/view/clone + GET html page) |
| `backend/context_packs.py` | **modify** | `_serialize_pack()` expose `share_count` + `has_active_shares` (สำหรับ pack card UI) |
| `backend/plan_limits.py` | **modify** | `check_pack_share_create_allowed()` + add `pack_share_limit_monthly` ใน PLAN_LIMITS |
| `legacy-frontend/app.html` | **modify** | Pack card menu "📤 Share..." button + Share Modal (whitelist + permission + TTL + privacy warning) + Shares Manager Modal (list + revoke + access log) |
| `legacy-frontend/app.js` | **modify** | 6 functions (open share modal, submit share, render shares list, revoke, copy link, render access log) + 12 i18n keys |
| `legacy-frontend/styles.css` | **modify** | `.share-modal`, `.share-recipient-list`, `.share-access-log`, `.privacy-warning` (~120 lines) |
| `legacy-frontend/shared_pack.html` | **create** (~200 lines) | Standalone recipient view page — display pack + clone button |
| `legacy-frontend/shared_pack.js` | **create** (~150 lines) | Auth check + render pack + clone action |
| `backend/config.py` + `app.html` | **modify** | bump APP_VERSION 9.2.1 → 9.3.0 |
| `scripts/share_pack_smoke.py` | **create** (~250 lines) | 30-case smoke test (privacy guards, TTL, revoke, clone, audit) |
| `tests/test_share_pack_v9_3.py` | **create** (~400 lines) | Comprehensive pytest (40+ cases: edge, race, quota, privacy, RBAC) |

**ไม่แตะ:** AI Pack Builder, retriever, graph_builder, MCP tools — out of scope

---

## 🗄️ Data Model Changes

### `PackShare` table — NEW

```python
class PackShare(Base):
    """v9.3.0 — Share link metadata. Token = JWT (stateless verify) แต่ row นี้
    เก็บ revocation + audience whitelist + audit trail ที่ JWT ไม่รองรับ."""
    __tablename__ = "pack_shares"
    id = Column(String, primary_key=True, default=gen_id)
    pack_id = Column(String, ForeignKey("context_packs.id"), nullable=False, index=True)
    owner_user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # Audience: email whitelist (JSON array of lowercase emails)
    allowed_emails = Column(Text, default="[]")

    # Permission: "view" | "view_clone"
    permission = Column(String, default="view_clone")

    # Lifecycle
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    revoke_reason = Column(String, nullable=True)   # owner-supplied reason

    # Stats (denormalized for fast UI render — actual log ใน PackShareAccess)
    access_count = Column(Integer, default=0)
    first_access_at = Column(DateTime, nullable=True)
    last_access_at = Column(DateTime, nullable=True)
    clone_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    pack = relationship("ContextPack")
    owner = relationship("User")


class PackShareAccess(Base):
    """v9.3.0 — Audit log แต่ละครั้งที่ recipient เข้าถึง shared pack.
    ใช้แสดงใน owner's "ใครเข้าดู pack ของฉัน" panel."""
    __tablename__ = "pack_share_accesses"
    id = Column(Integer, primary_key=True, autoincrement=True)
    share_id = Column(String, ForeignKey("pack_shares.id"), nullable=False, index=True)
    recipient_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    recipient_email = Column(String, nullable=True)
    action = Column(String, nullable=False)   # "view" | "clone"
    accessed_at = Column(DateTime, default=datetime.utcnow)
```

### Migration plan
ที่ `init_db()` — เพิ่ม `Base.metadata.create_all` จะสร้าง 2 ตารางใหม่อัตโนมัติเพราะ idempotent (existing tables ไม่ถูกแตะ)

### `users` + `context_packs` — ไม่เปลี่ยน

### `PLAN_LIMITS` — เพิ่ม
```python
"free":    { ..., "pack_share_limit_monthly": 1 },
"starter": { ..., "pack_share_limit_monthly": 50 },
"admin":   { ..., "pack_share_limit_monthly": 999999 },
```

### `UsageLog.action` — เพิ่ม value `"pack_share"` (ไม่ต้อง schema change — column เป็น String อิสระ)

---

## 🔌 API Changes

### 1. `POST /api/context-packs/{pack_id}/share` — NEW (สร้าง share)

**Request:**
```json
{
  "allowed_emails": ["alice@x.com", "bob@y.com"],
  "permission": "view_clone",
  "ttl_days": 30,
  "confirmed_privacy": true
}
```

**Response 200:**
```json
{
  "share_id": "shr_abc123",
  "share_token": "eyJ...",
  "share_url": "https://personaldatabank.fly.dev/shared/pack/eyJ...",
  "permission": "view_clone",
  "allowed_emails": ["alice@x.com", "bob@y.com"],
  "expires_at": "2026-06-06T...",
  "created_at": "..."
}
```

**Validation:**
- pack_id ต้องเป็นของ user (404 ถ้าไม่ใช่)
- pack ต้องไม่ locked (`is_locked=False`) — locked pack = ห้าม share
- `allowed_emails`: 1-20 emails, lowercase + valid format, dedupe
- `permission`: "view" | "view_clone"
- `ttl_days`: 1-90 (default 30)
- `confirmed_privacy`: ต้อง = True (UI bind กับ checkbox)
- Pack share quota check (`check_pack_share_create_allowed`)

**Errors:**
- `400 PACK_LOCKED` — pack is_locked=True
- `400 INVALID_EMAILS` — > 20 emails หรือ format ผิด
- `400 PRIVACY_NOT_CONFIRMED` — confirmed_privacy != true
- `400 TTL_OUT_OF_RANGE`
- `403 PACK_SHARE_QUOTA_REACHED`
- `404 PACK_NOT_FOUND`

### 2. `GET /api/context-packs/{pack_id}/shares` — NEW (list shares ของ pack นี้)

**Response 200:**
```json
{
  "shares": [
    {
      "share_id": "shr_abc",
      "allowed_emails": ["alice@x.com"],
      "permission": "view_clone",
      "expires_at": "...",
      "revoked_at": null,
      "access_count": 3,
      "clone_count": 1,
      "first_access_at": "...",
      "last_access_at": "...",
      "created_at": "..."
    }
  ],
  "count": 1
}
```

### 3. `DELETE /api/context-packs/shares/{share_id}` — NEW (revoke)

**Request body (optional):**
```json
{ "reason": "ส่งผิดคน" }
```

**Response 200:**
```json
{ "status": "revoked", "share_id": "shr_abc", "revoked_at": "..." }
```

**Behavior:** ตรวจ owner_user_id == current_user.id → set revoked_at + revoke_reason. Idempotent ถ้า revoke แล้ว.

### 4. `GET /api/shared/pack/{token}` — NEW (recipient view)

**Auth:** ต้อง login (JWT ของ user)

**Behavior:**
1. Decode JWT token (verify scope = `pack_share`)
2. Lookup PackShare row by share_id ใน payload
3. Check: revoked_at IS NULL + expires_at > now
4. Check: current_user.email อยู่ใน allowed_emails (lowercase compare)
5. Lookup pack — ถ้าหายไปแล้ว → 404 PACK_DELETED
6. Increment access_count + log PackShareAccess row
7. Return pack content (สรุป + intent + scope + source filenames + permission flag)

**Response 200:**
```json
{
  "pack": {
    "title": "...", "type": "study",
    "summary_text": "...", "intent": "...", "scope": "...",
    "source_filenames": ["calc.pdf", "alg.pdf"],
    "source_count": 2,
    "owner_name": "Tester",
    "owner_email_masked": "te***@x.com"
  },
  "permission": "view_clone",
  "share_id": "shr_abc",
  "expires_at": "..."
}
```

**Errors:**
- `401` — no JWT
- `403 EMAIL_NOT_ALLOWED` — login user.email ไม่อยู่ใน whitelist
- `403 SHARE_REVOKED`
- `404 SHARE_EXPIRED` หรือ `SHARE_NOT_FOUND`
- `404 PACK_DELETED`

### 5. `POST /api/shared/pack/{token}/clone` — NEW (clone to my workspace)

**Behavior:**
1. Verify share token (เหมือน #4) + check permission == "view_clone"
2. Pre-check: current_user pack quota (`check_pack_create_allowed`)
3. Create new ContextPack row owned by current_user — copy summary_text, intent, scope, type
4. **ไม่ copy source_file_ids** (recipient ไม่มี access ไฟล์ของ owner) → `source_file_ids="[]"`
5. Set `created_via="shared_clone"` (ใหม่ value — เพิ่มจาก manual/ai_builder)
6. Add metadata note ใน intent/scope: "(Cloned from {owner_name}'s pack)"
7. log PackShareAccess action="clone" + increment share.clone_count

**Response 200:** serialized new ContextPack ของ recipient

**Errors:**
- `403 PERMISSION_VIEW_ONLY` — share.permission == "view"
- `403 PACK_LIMIT_REACHED`

### 6. `GET /shared/pack/{token}` — NEW (HTML page)

**Behavior:** Serve `legacy-frontend/shared_pack.html` (parallel กับ `/app`, `/admin` pattern). JS ตรวจ auth + เรียก #4 + render

---

## 🛠️ Step-by-Step Implementation (สำหรับเขียว)

### Phase 1 — Backend foundation (~1.5 วัน)

**1.1 Schema migration** (`database.py`)
- เพิ่ม `class PackShare(Base)` + `class PackShareAccess(Base)`
- ที่ `init_db()` — ไม่ต้องเพิ่ม ALTER block (Base.metadata.create_all idempotent)

**1.2 Token signing** (`pack_share.py`)
- `sign_pack_share_token(share_id, ttl_seconds) -> str` — JWT scope="pack_share"
- `verify_pack_share_token(token) -> dict` — return {share_id, exp}
- `class ShareTokenError(Exception)` — parallel กับ `DownloadTokenError`

**1.3 Core operations** (`pack_share.py`)
- `create_share(db, user, pack_id, allowed_emails, permission, ttl_days) -> dict`
- `list_shares_for_pack(db, user, pack_id) -> list`
- `revoke_share(db, user, share_id, reason) -> dict`
- `get_shared_pack(db, current_user, token) -> dict` — verify + log access + return pack data
- `clone_shared_pack(db, current_user, token) -> dict` — verify + create_pack with created_via="shared_clone"

**1.4 Plan limits** (`plan_limits.py`)
- เพิ่ม `pack_share_limit_monthly` ใน 3 plans
- `check_pack_share_create_allowed(db, user) -> dict | None`
- `get_monthly_pack_share_count()` helper

**1.5 Endpoints** (`main.py`)
- 5 Pydantic models: `ShareCreateRequest`, `ShareRevokeRequest`, etc.
- 6 endpoints (POST share, GET shares, DELETE share, GET shared/pack/token, POST clone, GET /shared/pack/{token} HTML)

**1.6 Pack serialize** (`context_packs.py`)
- เพิ่ม `share_count` + `has_active_shares` ใน `_serialize_pack()`

**1.7 Version bump** — config.py 9.2.1 → 9.3.0

### Phase 2 — Frontend (~1.5 วัน)

**2.1 Pack card menu — Share button**
- เพิ่มปุ่ม "📤" ข้าง "🔄" และ "🗑" ใน `.pack-card-actions`
- onclick → `openShareModal(packId)`
- Badge: ถ้า `pack.has_active_shares` → แสดง "🔗 N shared" ใน meta

**2.2 Share Modal**
- Steps:
  1. **Privacy warning** — แสดง list source files + checkbox "เข้าใจว่าสรุป + ชื่อไฟล์ ({N} ไฟล์) จะถูก share"
  2. **Recipient input** — email whitelist (chip-based input, max 20)
  3. **Permission** — radio: "ดูอย่างเดียว" / "ดู + clone ได้"
  4. **TTL** — slider/select: 7/14/30/60/90 วัน (default 30)
  5. **Submit** — ส่ง POST → ได้ share_url → แสดง + copy button

**2.3 Shares Manager Modal**
- คลิก badge "🔗 N shared" → modal แสดง list shares
- แต่ละ row: emails + permission + expires_at + access count + revoke button
- Click row → expand audit log (PackShareAccess timeline)

**2.4 Recipient view (`shared_pack.html`)**
- Standalone page ที่ JS:
  - check localStorage.pdb_token → ถ้าไม่มี redirect /
  - GET `/api/shared/pack/{token}`
  - Render: title + intent + scope + summary_text + source filenames + owner
  - ถ้า permission = "view_clone" → แสดงปุ่ม "📥 Clone to my workspace"
  - หลัง clone → toast + redirect /app#pack/{new_id}

**2.5 i18n** — 12 keys TH+EN

### Phase 3 — Tests (~0.5 วัน)

**3.1 `scripts/share_pack_smoke.py`** — 30 cases
**3.2 `tests/test_share_pack_v9_3.py`** — 40+ pytest cases

---

## 🧪 Test Scenarios (สำหรับฟ้า)

### Group A: Happy path (5)
- T-A1 Owner create share → return token + URL + DB row
- T-A2 Recipient (in whitelist) view → 200 + content + access_count++
- T-A3 Recipient clone → new pack ใน workspace ของตัวเอง + clone_count++
- T-A4 Owner list shares → ครบ
- T-A5 Owner revoke share → revoked_at set → recipient view → 403

### Group B: Privacy guards (6)
- T-B1 `confirmed_privacy=false` → 400
- T-B2 Locked pack → 400 PACK_LOCKED (ห้าม share)
- T-B3 Email ไม่อยู่ใน whitelist → 403 EMAIL_NOT_ALLOWED
- T-B4 Whitelist > 20 emails → 400 INVALID_EMAILS
- T-B5 Email format ผิด → 400 INVALID_EMAILS
- T-B6 source_file_ids ไม่หลุดใน clone (recipient ไม่ได้ access ไฟล์ owner)

### Group C: Lifecycle + revoke (5)
- T-C1 Expired token (ttl_days+1 ผ่าน) → 404 SHARE_EXPIRED
- T-C2 Revoked share → 403 SHARE_REVOKED
- T-C3 Pack deleted หลัง share สร้าง → 404 PACK_DELETED
- T-C4 Revoke twice → idempotent (no error)
- T-C5 TTL = 91 days → 400 TTL_OUT_OF_RANGE

### Group D: Permission + clone (5)
- T-D1 permission="view" → POST clone → 403 PERMISSION_VIEW_ONLY
- T-D2 permission="view_clone" + recipient pack quota เต็ม → 403 PACK_LIMIT_REACHED
- T-D3 Cloned pack: source_file_ids=[] (privacy)
- T-D4 Cloned pack: created_via="shared_clone"
- T-D5 Cloned pack: title/intent/scope copied + summary มี note "Cloned from..."

### Group E: Quota + audit (5)
- T-E1 Free user 1 active share → create another → 403
- T-E2 Free user revoke active → can create new ⚠️ (decision: revoked shares ยังนับ quota เดือนนี้ไหม? — แนะนำ: นับ — กัน abuse)
- T-E3 Starter user 50 shares ใช้ครบ → 403
- T-E4 Audit log ทุก view + clone action
- T-E5 access stats (count, first/last) sync กับ log table

### Group F: Auth + cross-user (4)
- T-F1 No JWT view shared → 401
- T-F2 Other user (not owner, not in whitelist) → 403
- T-F3 Owner cannot revoke share ของ user อื่น → 404
- T-F4 Recipient view masks owner_email (te***@x.com)

### Group G: Edge cases (5)
- T-G1 Whitelist 0 emails → 400
- T-G2 Duplicate emails ใน whitelist → dedupe + accept
- T-G3 Recipient view = owner login (owner.email ก็อยู่ใน whitelist) → ทำงานได้ + access_count++
- T-G4 Concurrent view 5 ครั้งพร้อมกัน → access_count == 5 (atomic)
- T-G5 Token signed ที่ secret rotate แล้ว → INVALID_TOKEN

### Frontend (4 manual)
- F1 Open share modal → privacy warning + checkbox required → submit only if checked
- F2 Share URL copy button → clipboard works
- F3 Recipient view UI ที่ /shared/pack/{token} — render correct + clone button visible
- F4 Mobile (375px): share modal usable + recipient view responsive

---

## ✅ Done Criteria

- [ ] 2 new tables created via init_db (no migration needed)
- [ ] `pack_share.py` module + 6 endpoints
- [ ] Plan limit `pack_share_limit_monthly` enforced
- [ ] Frontend: share modal + manager modal + recipient view (`shared_pack.html` + `.js`)
- [ ] Privacy: confirmation checkbox + locked-pack guard + email whitelist
- [ ] Audit: PackShareAccess log + UI display
- [ ] Smoke 30/30 + pytest 40+/40+ pass
- [ ] Regression v9.0.1 + v9.2.0 ยังผ่าน
- [ ] APP_VERSION 9.2.1 → 9.3.0
- [ ] 5 commits แยก logical:
  1. `feat(db): pack_shares + pack_share_accesses tables [v9.3.0]`
  2. `feat(api): pack_share module + token signing [v9.3.0]`
  3. `feat(api): 6 share endpoints + plan limits [v9.3.0]`
  4. `feat(frontend): share modal + manager + recipient view [v9.3.0]`
  5. `chore: bump APP_VERSION 9.3.0 + smoke + pytest + memory`

---

## ⚠️ Risks / Open Questions

### Risks
1. **R1 — Privacy leak** — owner share pack แต่ลืมว่ามีไฟล์ sensitive → recipient เห็นชื่อ → Mitigation: confirmation modal บังคับ checkbox + แสดง list ไฟล์เต็ม
2. **R2 — Token JWT ขนาดใหญ่ → URL ยาว** — ทำให้ paste ใน chat ยาก → Mitigation: TTL สั้นๆ ทำให้ payload เล็ก
3. **R3 — Recipient clone → owner ลบ pack เดิม → cloned pack เดิม → confused** → Mitigation: cloned pack มี note "Cloned from {owner_name}'s pack on {date}" ใน intent
4. **R4 — Revoked share ยังใช้งานได้ ถ้า recipient เปิดอยู่** — JWT verify pass + DB row check rejects → ✅ ฝั่ง server ตรวจ revoked_at ทุก request
5. **R5 — DDoS via cloning** — recipient clone repeated → fill DB → Mitigation: clone นับ pack quota ของ recipient (existing limit)
6. **R6 — Email enumeration** — ถ้า user A share to alice@x → alice login → access_count++. attacker ลอง login เป็น email ต่างๆ → ติดที่ JWT auth (ต้องผ่าน register ก่อน)
7. **R7 — Stripe downgrade ระหว่างมี active shares** — Free 1 share, user มี 5 shares ตอน Starter → downgrade → shares ส่วนเกิน?  → Mitigation v9.3: ไม่ auto-revoke — user เห็น "5/1 shares — เกิน quota" ใน UI + ต้อง revoke เอง (parallel กับ pack lock pattern)
8. **R8 — Pack changed after share** — owner regenerate pack → recipient เห็น content ใหม่ → ✅ feature ที่ดี (live link) — แต่ต้องบอก user ใน UI

### Open Questions (Q1-Q8 — มี default ทุกข้อ)
- **Q1** Recipient ที่ login แต่ไม่อยู่ใน whitelist → 403 message? → **Default:** "ลิงก์นี้ไม่ได้แชร์ให้คุณ — ติดต่อเจ้าของลิงก์"
- **Q2** Owner mask email หรือไม่ใน recipient view? → **Default: mask** (te***@x.com — privacy)
- **Q3** Cloned pack title prefix? → **Default:** ใช้ title เดิม + intent ต่อท้าย "(Cloned from {owner})"
- **Q4** revoked_at + expires_at ผ่านแล้ว → DB GC ไหม? → **Default:** ไม่ GC ใน v9.3 (audit history) — เพิ่ม cleanup script ภายหลัง
- **Q5** Share badge text ใน pack card? → **Default:** "🔗 {N} shared" / "🔗 1 shared"
- **Q6** Recipient view เห็น owner_name หรือ owner_email? → **Default:** name only (mask email — privacy)
- **Q7** Clone confirmation? — recipient กด clone ต้อง confirm 2nd time ไหม? → **Default:** ไม่ต้อง — กด 1 ครั้งสำเร็จ + toast confirm
- **Q8** TTL options ใน UI dropdown? → **Default:** 7, 14, **30 (default)**, 60, 90 วัน

---

## 📝 Notes for เขียว (gotchas + reuse patterns)

### Gotchas
1. **JWT token + DB row dual-check** — token verify ต้องตามด้วย DB lookup (revoked? expired? owner deleted pack?). อย่า trust JWT alone
2. **Email lowercase normalize** — ทั้ง whitelist + recipient comparison ต้อง lowercase ก่อน
3. **`current_user.email` อาจเป็น NULL** (Google-only signup ก่อน v8.1) — handle case นี้ใน whitelist check (ถ้า email = NULL → 403)
4. **Atomic access_count update** — `UPDATE ... SET access_count = access_count + 1` (ไม่ใช่ read-modify-write Python) เพื่อกัน race
5. **Cloned pack มี source_file_ids = []** — ห้าม copy IDs ของ owner เพราะ recipient ไม่มี access. UI clone จะแสดง "ไม่มีไฟล์ source" — เป็น expected behavior
6. **Pack regenerate หลัง share** — recipient view = live (ไม่ snapshot) → owner ระวัง. UI แสดง "Last updated: {pack.updated_at}" ใน recipient view
7. **TTL 90 วัน max** — ถ้า business case ต้องนานกว่า → user revoke + create ใหม่ (กัน orphan link)
8. **Recipient view URL pattern** `/shared/pack/{token}` — token = JWT ที่มี share_id ฝัง. ต่างจาก `/d/{token}` (signed file download) ตรง scope
9. **Frontend share modal — privacy checkbox** ต้อง bind disabled state กับ submit button (เปิด checkbox ก่อนกดได้)

### Reuse patterns
- ดู [backend/signed_urls.py](../../backend/signed_urls.py) เป็น template สำหรับ JWT scoped token
- ดู [backend/admin.py](../../backend/admin.py) `list_audit_logs` เป็น template สำหรับ paginated list
- ดู [backend/context_packs.py](../../backend/context_packs.py) `create_pack` เพื่อตามแบบ create flow ใน clone_shared_pack
- ดู [legacy-frontend/admin.html:172-201](../../legacy-frontend/admin.html#L172) เพื่อ confirmation modal pattern
- ดู [tests/test_ai_pack_builder_v9_2.py](../../tests/test_ai_pack_builder_v9_2.py) เป็น template comprehensive pytest

### Out of scope guard
- ❌ ไม่ทำ subscribe/auto-sync (v9.4.0)
- ❌ ไม่ share ไฟล์ source (privacy red line)
- ❌ ไม่ public link (anyone-with-link) — v9.3 = email whitelist only
- ❌ ไม่ password-protected link (v9.4.0+)
- ❌ ไม่ MCP tool create_share (v9.4.0)

---

## 📋 Pipeline Next

1. 🔴 **User review plan** — ตอบ Q1-Q8 (หรือยอมรับ default)
2. 🟢 **เขียวเริ่ม build** — Phase 1 → 2 → 3 (~3 วัน)
3. 🔵 **ฟ้า review** — verify privacy guards + 70+ test cases
4. 🔴 **User approve + push + deploy**

---

## 🔗 Strategic alignment

**PDB brand promise (จาก project_pdb_brand_voice memory):**
> "เก็บอย่างดี + เป็นส่วนตัว + เป็นระบบ"

Pack sharing = ขยับจาก "ใช้คนเดียว" → "share อย่างควบคุมได้" — **เพิ่ม value โดยไม่ทำลาย privacy core** เพราะ:
- ✅ Default = private (ไม่ share ถ้าไม่กด)
- ✅ Email whitelist = ไม่ใช่ public
- ✅ Source content ไม่ leak (แค่สรุป + ชื่อไฟล์)
- ✅ Revoke ได้ทุกเมื่อ
- ✅ Audit ครบ (ใครเข้า เมื่อไหร่)

นี่ไม่ใช่ "share" แบบ Google Drive (everything-with-link) — เป็น **"share knowledge artifact ที่กลั่นแล้ว"** ที่เน้น privacy
