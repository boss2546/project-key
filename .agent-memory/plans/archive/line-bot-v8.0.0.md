# Plan: LINE Bot Integration — Personal Knowledge in LINE ⭐ MAIN FOCUS

> ✅ **REVISED 2026-05-02 (3rd time)** — User pivot: LINE bot = main focus, defer other systems
> See [handoff/supervisor-briefing-line-bot.md](../handoff/supervisor-briefing-line-bot.md) for project coordination
> **Streamlined sequence:** v7.6.0 Section A ✅ DONE + Section C (signed URLs only) → v8.0.0 LINE Bot D-K

**Author:** แดง (Daeng)
**Date:** 2026-05-02 (3rd revision — LINE-focused)
**Status:** `plan_pending_approval` (main focus)
**Target version:** **v8.0.0**
**Estimated effort:**
- Foundation prerequisites remaining: ~1-2 days (Section C signed URLs only)
- LINE Bot phases D-K: ~3-4 weeks
- **Total: ~3.5-4.5 weeks** (down from ~6-7 weeks original bundle)

**Foundation prerequisite (minimum):**
- ✅ Section A DONE (plan_limits + email service) — awaiting commit
- 🔴 Section C TODO (signed URLs `/d/{token}`) — REQUIRED for file delivery
- ⏸️ Section B DEFERRED (MCP USP — not needed for LINE)

**Reuses:**
- v7.6.0 Section A: `check_upload_allowed`, `email_service`
- v7.6.0 Section C: `signed_urls`, `GET /d/{token}` (after build)
- Existing: `extract_text`, `compute_content_hash`, `storage_router`, `vector_search`, `/api/chat`

---

## 🎯 Goal

ทำให้ลูกค้าไทยสามารถใช้ PDB ผ่าน **LINE bot** ได้ — เป็น **distribution moat** ในตลาดไทย

**ผู้ใช้ที่ได้ประโยชน์:**
- Thai knowledge worker / professional / student (90%+ adoption ของ GenAI ในไทย)
- คนที่ใช้ LINE ทุกวัน (54-56M Thai users)
- Power user ที่อยาก access PDB ผ่าน mobile โดยไม่เปิดเว็บ

**ทำเสร็จแล้วได้อะไร:**
1. **Distribution moat ในไทย** — Thai market = LINE-first; web-only = สู้ Alisa ไม่ได้
2. **Killer aha moments** — Forward link → 30s summary, ถามตอนประชุม → 3s ตอบ
3. **Habit-forming product** — LINE = daily-use → user เห็น bot ทุกวัน
4. **Reduce signup friction** — add bot → onboard ผ่าน LINE Login OAuth → no separate signup
5. **First-mover ใน Thai PKM space** — ไม่มี Thai service ทำ "personal knowledge management + LINE bot"
6. **Path สำหรับ Telegram + Discord ทีหลัง** — design adapter pattern ตั้งแต่ต้น

---

## ✅ Resolved Decisions (จาก user 2026-05-02)

| # | Decision | สถานะ |
|---|---|---|
| Q1 | Scope MVP = 8 features (account link + upload + chat + search + ขอไฟล์ + stats + forward + welcome flow) | ✅ baked-in |
| Q2 | Account linking = Option A — **user-initiated จาก LINE** → bot ส่ง prompt → web login → mapping | ✅ baked-in |
| Q3 | Welcome flow = หลัง link สำเร็จ bot **introduce ตัวเอง + รายงานสถานะตู้** (3 messages: greeting + status Flex + capabilities + Quick Reply) | ✅ baked-in |
| Q4 | Storage routing = respect `user.storage_mode` เหมือน HTTP upload | ✅ baked-in |
| Q5 | Plan limits = ใช้ `check_upload_allowed()` เดียวกัน — MCP/LINE ห้าม bypass quota | ✅ baked-in |
| Q6 | Rich Menu = 6-tile (อัพโหลด/ค้นหา/ถาม AI/รายการ/ตั้งค่า/เปิดเว็บ) | ✅ baked-in |
| Q7 | Bot adapter pattern — design abstraction ตั้งแต่ Phase 1 ให้ Telegram/Discord ตามมาง่าย | ✅ baked-in |

---

## 📚 Context

### Why LINE first (not Telegram/Discord)
- **Thai market reach:** LINE 56M users (95% Thai internet) vs Telegram ~few million vs Discord niche
- **No Thai PKM competitor** — wide-open lane
- **Free tier sufficient for MVP:** Communication plan = ฿0, Reply API ไม่นับ quota
- **First-mover advantage** — ตลาด PKM ในไทย = empty

### Why need bot abstraction layer
- 3-platform future (LINE → Telegram → Discord) — เขียน adapter pattern Phase 1 ลด rework Phase 2/3
- Logic จริง (search, upload, pack) เขียนครั้งเดียวใน `bot_handlers.py`
- Each platform adapter แค่แปลง output → format ของตัวเอง

### LINE Bot Limitations ที่ยอมรับ
1. ❌ **Bot ส่ง PDF/DOCX กลับ user ไม่ได้** → workaround: Flex card + signed download URL (Thai users คุ้นเคย — SCB/KBank pattern)
2. ❌ **No markdown** in text → workaround: ใช้ Flex Message สำหรับ formatted content
3. ⚠️ **Reply token expires 30 sec** → ack webhook 200 ทันที + use Push API for slow ops
4. ⚠️ **Push quota 200/month free** → ใช้ push เฉพาะ critical events; ห้าม spam
5. ⚠️ **Inbound file retention ~14 days** → download ทันทีบน webhook
6. ⚠️ **LINE Notify ปิดตัว April 2025** — ห้ามใช้

### Authentication Architecture
- Use **LINE's Account Link feature** (canonical pattern):
  1. `POST /v2/bot/user/{userId}/linkToken` → get linkToken
  2. Redirect user to `https://access.line.me/dialog/bot/accountLink?linkToken=X&nonce=Y`
  3. After success, LINE sends `accountLink` webhook event with same nonce + LINE userId
  4. Match nonce to PDB user_id → save mapping
- **PDB web side:** add `/auth/line` page รับ linkToken → ถ้า user logged in → confirm → redirect callback. ถ้ายัง → show login/register first.

---

## 📁 Files to Create / Modify

### 🆕 Backend — Create
- `backend/line_bot.py` (~600 lines) — LINE webhook handler, send/receive logic, signature verify
- `backend/bot_handlers.py` (~400 lines) — **platform-agnostic** command handlers (intent detection, search, stats, file lookup)
- `backend/bot_adapters.py` (~200 lines) — `BotAdapter` abstract base + `LineBotAdapter` impl (Telegram/Discord adapters เพิ่มทีหลัง)
- `backend/bot_messages.py` (~300 lines) — Flex Message builders (status card, file card, search results carousel, etc.)
- `backend/signed_urls.py` (~80 lines) — JWT-signed download URLs (`/d/{token}` endpoint helper)

### 🔧 Backend — Modify
- `backend/main.py` — เพิ่ม:
  - `POST /webhook/line` — LINE webhook endpoint
  - `GET /auth/line` — account link landing page (HTML)
  - `POST /api/line/confirm-link` — confirm link from web
  - `GET /api/line/status` — admin status (active users count, message count today)
  - `GET /d/{token}` — signed download endpoint (universal, ไม่ใช่ LINE-specific)
- `backend/database.py` — เพิ่ม `LineUser` model + idempotent migration (ADD-only ตาม DB-003)
- `backend/config.py` — เพิ่ม env vars: `LINE_CHANNEL_SECRET`, `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_LOGIN_CHANNEL_ID`, `LINE_LOGIN_CHANNEL_SECRET`, `LINE_BOT_BASE_URL`
- `requirements.txt` — เพิ่ม `line-bot-sdk>=3.0.0`, `PyJWT>=2.8.0` (ถ้ายังไม่มี)
- `Dockerfile` — verify `line-bot-sdk` install ใน Fly deploy

### 🆕 Frontend — Create
- `legacy-frontend/auth-line.html` — minimal landing page สำหรับ LINE account link confirm
- `legacy-frontend/auth-line.js` — handler logic
- `legacy-frontend/line-rich-menu.png` — 2500×1686 image สำหรับ Rich Menu (6 tiles)
  - ⚠️ Note for เขียว: ใช้ Figma หรือ Canva สร้างแล้ว export PNG. Color scheme: indigo + dark.

### 🔧 Frontend — Modify
- `legacy-frontend/app.html` — Profile section เพิ่ม "เชื่อม LINE Bot" button (alternative entry — Web → LINE)
- `legacy-frontend/app.js` — เพิ่ม `loadLineStatus()` + `disconnectLine()` functions
- `legacy-frontend/styles.css` — styles สำหรับ LINE section ใน profile

### 🆕 Tests (สำหรับ ฟ้า)
- `tests/test_line_bot.py` — unit tests สำหรับ webhook handler, signature verify, intent detection
- `tests/test_bot_handlers.py` — platform-agnostic handler tests (mock adapter)
- `tests/test_signed_urls.py` — JWT signing + verification + expiry
- `tests/e2e-ui/line-flow.spec.js` — Playwright E2E: account link landing page
- `scripts/line_bot_smoke.py` — in-process smoke test (mock LINE webhook events) — ตาม TEST-002 pattern

---

## 📡 API Changes

### POST `/webhook/line` (NEW — public, signature-verified)
**Auth:** ไม่มี JWT — ใช้ LINE signature verification (`X-Line-Signature` header = HMAC-SHA256(channel_secret, raw_body))

**Request:** LINE webhook event payload (varies by event type)
```json
{
  "destination": "U...",
  "events": [
    {
      "type": "message" | "follow" | "unfollow" | "accountLink" | "postback" | "memberJoined",
      "source": {"userId": "U...", "type": "user"},
      "timestamp": 1714680000000,
      "replyToken": "...",
      "message": {
        "type": "text" | "image" | "video" | "audio" | "file",
        "id": "12345",
        "text": "..." | "fileName": "report.pdf", "fileSize": 12345
      }
    }
  ]
}
```

**Response 200 (always — ack ทันทีก่อนทำงานจริง):**
```json
{ "status": "ok" }
```

**Errors:**
- 401 `INVALID_SIGNATURE` — HMAC verify fail
- 400 `INVALID_PAYLOAD` — JSON malformed

**Handler logic:**
1. Verify `X-Line-Signature`
2. Parse events
3. Ack 200 immediately
4. **Background task:** dispatch each event to `handle_line_event()` (use FastAPI `BackgroundTasks`)
5. Errors logged but don't propagate

---

### GET `/auth/line?linkToken=X` (NEW — public HTML)
**Purpose:** landing page after user clicks "เชื่อมบัญชี" ใน bot

**Behavior:**
- Read `linkToken` query param
- Check JWT cookie / Authorization → if logged in:
  - Show "เชื่อมบัญชี LINE 'XYZ' กับบัญชี PDB ของคุณ?" + Confirm button
- If not logged in:
  - Show login form (PDB email/password) + "หรือเข้าสู่ระบบด้วย LINE Login" option
  - After login → loop back to confirm step
- Confirm → POST `/api/line/confirm-link`
- Success → redirect to `line://oaMessage/{lineBotId}` deep link
- Error → show error + retry button

---

### POST `/api/line/confirm-link` (NEW — JWT auth required)
**Auth:** `Depends(get_current_user)`

**Request:**
```json
{ "link_token": "abc..." }
```

**Response 200:**
```json
{
  "status": "linked",
  "line_display_name": "John Doe",
  "redirect_url": "line://oaMessage/...",
  "nonce": "..."
}
```

**Behavior:**
1. Decode `link_token` (JWT signed, 5-min expiry)
2. Generate random `nonce` (≥128 bits, base64)
3. Save `LineUser` row with `link_nonce = nonce`, `link_nonce_expires_at = now + 10min`
4. Build redirect URL: `https://access.line.me/dialog/bot/accountLink?linkToken={extracted}&nonce={nonce}`
5. Return URL — frontend redirects user

**Errors:**
- 401 `UNAUTHORIZED` — JWT missing
- 400 `EXPIRED_LINK_TOKEN`
- 409 `ALREADY_LINKED` — pdb_user already has line_user row

---

### GET `/api/line/status` (NEW — JWT auth required)
**Response:**
```json
{
  "linked": true,
  "line_display_name": "John Doe",
  "linked_at": "2026-05-02T10:00:00Z",
  "last_seen_at": "2026-05-02T15:30:00Z"
}
```

---

### POST `/api/line/disconnect` (NEW — JWT auth required)
**Behavior:** Delete `LineUser` row + send notify to bot user (push) "บัญชีถูก unlink แล้ว"

**Response 200:**
```json
{ "status": "disconnected" }
```

---

### GET `/d/{token}` (NEW — public, JWT-verified)
**Purpose:** signed download URL for files (universal — ใช้ใน LINE Flex card, MCP, หรือ web sharing)

**Token payload (JWT signed with `JWT_SECRET_KEY`):**
```json
{
  "file_id": "abc123",
  "user_id": "xyz789",
  "exp": 1714683600,
  "iat": 1714680000,
  "scope": "download"
}
```

**Response:**
- Token valid → `FileResponse` ของไฟล์ (ใช้ logic เดียวกับ `/api/files/{id}/download` แต่ไม่ต้อง JWT auth)
- Token expired → 410 `LINK_EXPIRED`
- Token invalid → 401
- File not found → 404
- File belongs to different user → 403

**Default expiry:** 30 minutes
**Configurable:** `?ttl=300` (max 3600 sec / 1 hour)

---

## 💾 Data Model Changes

### New table: `line_users`
```python
class LineUser(Base):
    """Mapping LINE user → PDB user (1 PDB user → 1 LINE account in MVP)."""
    __tablename__ = "line_users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    line_user_id = Column(String, unique=True, nullable=False, index=True)
    pdb_user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    line_display_name = Column(String, nullable=True)

    # Account linking flow
    link_nonce = Column(String, nullable=True)  # for accountLink webhook verify
    link_nonce_expires_at = Column(DateTime, nullable=True)

    # State
    welcomed = Column(Boolean, default=False)  # has shown welcome flow?
    rich_menu_id = Column(String, nullable=True)  # which rich menu attached

    # Timestamps
    linked_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    unlinked_at = Column(DateTime, nullable=True)  # soft-delete (preserve history)

    # FK
    user = relationship("User", backref="line_account")
```

### Migration (idempotent ตาม DB-003)
```python
# Inside init_db() in database.py
cursor = await db.execute("PRAGMA table_info(line_users)")
exists = await cursor.fetchall()
if not exists:
    # create_all() handles this — table will be created from class
    print("  → Created: line_users table (LINE bot integration)")

# Optional: index on line_user_id (already in column def, but verify)
try:
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_line_users_line_id "
        "ON line_users(line_user_id)"
    )
except Exception as e:
    print(f"  ⚠️ line_users index: {e}")
```

**Why no other table changes:** ทุกอย่าง reuse `users`, `files`, `clusters`, etc. ที่มีอยู่แล้ว

---

## 🔧 Step-by-Step Implementation (สำหรับเขียว)

### Phase 1 — Foundation (~3-4 วัน)

#### Step 1.1: Setup dependencies + config
1. เพิ่ม `requirements.txt`:
   ```
   line-bot-sdk>=3.0.0
   PyJWT>=2.8.0  # ถ้ายังไม่มี (verify)
   ```
2. แก้ `backend/config.py` เพิ่ม:
   ```python
   # ─── LINE Bot Integration (v8.0.0) ───
   LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
   LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
   LINE_LOGIN_CHANNEL_ID = os.getenv("LINE_LOGIN_CHANNEL_ID", "")
   LINE_LOGIN_CHANNEL_SECRET = os.getenv("LINE_LOGIN_CHANNEL_SECRET", "")
   LINE_BOT_BASIC_ID = os.getenv("LINE_BOT_BASIC_ID", "")  # @PDBBot

   def is_line_configured() -> bool:
       """True if LINE bot env vars complete. Used to gate /webhook/line + UI button."""
       return bool(LINE_CHANNEL_SECRET and LINE_CHANNEL_ACCESS_TOKEN)
   ```
3. Update `.env.example` document พร้อม comment instructions
4. ลงทะเบียน `LINE_CHANNEL_SECRET` ฯลฯ ใน Fly.io secrets via `fly secrets set`

#### Step 1.2: Add `line_users` table + migration
1. เพิ่ม `LineUser` class ใน `backend/database.py` (full schema ด้านบน)
2. เพิ่ม migration block ใน `init_db()` — idempotent + auto-backup
3. ทดสอบ: รัน `python -m backend.main` → ดู log "Created: line_users table"

#### Step 1.3: Create `backend/signed_urls.py`
```python
"""JWT-signed URLs for downloading user files via LINE Flex / MCP / shared links."""
import jwt
from datetime import datetime, timedelta, timezone
from .config import JWT_SECRET_KEY, JWT_ALGORITHM

def sign_download_url(file_id: str, user_id: str, ttl_seconds: int = 1800) -> str:
    """Return signed token. Default TTL = 30 min."""
    payload = {
        "file_id": file_id,
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
        "iat": datetime.now(timezone.utc),
        "scope": "download",
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def verify_download_token(token: str) -> dict:
    """Decode + verify. Raises jwt.ExpiredSignatureError, jwt.InvalidTokenError."""
    payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    if payload.get("scope") != "download":
        raise jwt.InvalidTokenError("Invalid scope")
    return payload
```

4. เพิ่ม endpoint `GET /d/{token}` ใน `main.py`:
   - Verify token → load File → check user_id ตรงกัน → return FileResponse

#### Step 1.4: Create `backend/bot_adapters.py` skeleton
```python
"""Platform-agnostic bot adapter interface. Future: TelegramBotAdapter, DiscordBotAdapter."""
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class BotMessage:
    text: str | None = None
    flex: dict | None = None  # Flex JSON
    quick_reply: list[dict] | None = None
    file_url: str | None = None  # for platforms that can send files (Telegram/Discord)

class BotAdapter(ABC):
    """Abstract bot adapter — each platform implements own send/receive logic."""

    @abstractmethod
    async def send_message(self, recipient_id: str, message: BotMessage) -> None: ...

    @abstractmethod
    async def download_attachment(self, message_id: str) -> tuple[bytes, str, str]:
        """Return (bytes, filename, mime_type)."""
        ...

    @abstractmethod
    async def show_typing(self, recipient_id: str, duration_sec: int = 5) -> None: ...

class LineBotAdapter(BotAdapter):
    """Implementation backed by line-bot-sdk-python."""
    # Filled in Phase 2
    pass
```

#### Step 1.5: Webhook endpoint + signature verify
1. ใน `main.py` เพิ่ม:
   ```python
   from fastapi import BackgroundTasks
   from .line_bot import handle_line_event, verify_signature

   @app.post("/webhook/line")
   async def line_webhook(
       request: Request,
       background_tasks: BackgroundTasks,
       x_line_signature: str = Header(None),
   ):
       if not is_line_configured():
           return JSONResponse({"error": {"code": "LINE_NOT_CONFIGURED"}}, status_code=503)
       body = await request.body()
       if not verify_signature(body, x_line_signature):
           raise HTTPException(401, "INVALID_SIGNATURE")
       payload = json.loads(body)
       for event in payload.get("events", []):
           background_tasks.add_task(handle_line_event, event)
       return {"status": "ok"}
   ```

2. สร้าง `backend/line_bot.py` skeleton:
   - `verify_signature(body: bytes, signature: str) -> bool` — HMAC-SHA256
   - `handle_line_event(event: dict) -> None` — dispatcher (placeholder return)

3. ทดสอบ local: ใช้ ngrok + LINE webhook tester → ดู log "Event received: follow"

**Done criteria Phase 1:**
- [ ] `line_users` table created
- [ ] `/webhook/line` returns 200 + verifies signature
- [ ] `/d/{token}` works (test with hand-signed token)
- [ ] BotAdapter abstract class defined

---

### Phase 2 — Account Linking + Welcome Flow (~3-4 วัน)

#### Step 2.1: `follow` event handler (user adds bot)
1. Implement `_handle_follow(event)` ใน `line_bot.py`:
   - Get LINE userId from event
   - Check: ถ้ามี LineUser row ที่ active → silent (re-follow scenario)
   - ถ้าไม่มี → ส่ง greeting message:
     ```
     "ยินดีต้อนรับสู่ Personal Data Bank! 👋
      ผมเป็นผู้ช่วยจัดการข้อมูลส่วนตัวของคุณ
      ก่อนเริ่มใช้งาน — กรุณาเชื่อมบัญชีก่อนครับ"

      [ปุ่ม URI Action: "เชื่อมบัญชี PDB"]
      → URL: https://pdb.app/auth/line?linkToken={LINE_TOKEN}
     ```
   - **Get linkToken:** call `POST /v2/bot/user/{userId}/linkToken` (LINE API) → get linkToken
   - Build URI = `https://pdb.app/auth/line?linkToken={linkToken}`
   - Send via `replyMessage` API (use replyToken, fast — under 30 sec)

#### Step 2.2: `/auth/line` landing page
1. Backend: `GET /auth/line` returns `auth-line.html` (static)
2. Frontend `auth-line.html` + `auth-line.js`:
   - Read `linkToken` query
   - Check `pdb_token` localStorage (already logged in?)
   - If logged in → show confirm UI ("เชื่อม LINE กับบัญชี user@example.com?")
   - If not → show login form (reuse `landing.js` auth flow) → after login → confirm
   - Confirm button → `POST /api/line/confirm-link {link_token}` with JWT
   - Success → redirect to `redirect_url` from response (line:// deep link)

#### Step 2.3: `POST /api/line/confirm-link`
1. Decode `link_token` → extract LINE linkToken
2. Generate random `nonce` (32 bytes urlsafe base64)
3. Insert/update `LineUser` row:
   - `pdb_user_id` = current user
   - `line_user_id` = NULL ในตอนนี้ (จะถูก fill ใน accountLink event)
   - `link_nonce` = nonce
   - `link_nonce_expires_at` = now + 10 min
4. Return:
   ```json
   {
     "status": "linked",
     "redirect_url": "https://access.line.me/dialog/bot/accountLink?linkToken=<linkToken>&nonce=<nonce>"
   }
   ```
5. Frontend redirect → user คลิก authorize ใน LINE → LINE ยิง webhook event `accountLink` กลับมา

#### Step 2.4: `accountLink` webhook event handler
1. Implement `_handle_account_link(event)`:
   - Extract `event.link.nonce` + `event.source.userId`
   - Find `LineUser` ที่ `link_nonce == nonce` AND `link_nonce_expires_at > now`
   - Set `line_user_id = userId` (now we know who they are in LINE)
   - Clear `link_nonce` (one-time use)
   - Update `welcomed = false` (will trigger welcome flow next step)
2. Trigger welcome flow (Step 2.5)

#### Step 2.5: Welcome flow (3 messages)
1. Implement `send_welcome(line_user_id, pdb_user_id)`:
   - Load PDB user data (name, plan, file count, etc.)
   - **Message 1 (text):**
     ```
     "สวัสดี {user.name} 👋
      ผม PDB Assistant — ผู้ช่วยจัดการข้อมูลส่วนตัวของคุณครับ
      เชื่อมต่อสำเร็จแล้ว ✅"
     ```
   - **Message 2 (Flex card "สถานะตู้"):** ใช้ builder ใน `bot_messages.py`:
     - File count, collection count, context pack count
     - Storage mode (managed/byos)
     - Storage usage (MB used / limit MB)
     - Pending unprocessed files (ถ้ามี — show "จัดระเบียบเลย" button)
   - **Message 3 (text + Quick Reply):**
     ```
     "ผมทำอะไรได้บ้าง 👇
      📤 ส่งไฟล์ให้ผม → จัดให้อัตโนมัติ
      💬 ถามคำถามจากข้อมูลในตู้
      🔍 ค้นหาไฟล์ที่เกี่ยวข้อง
      📚 สร้าง Context Pack ส่งต่อให้ AI ตัวอื่น
      📥 ขอไฟล์กลับ → ส่ง download link

      ลองพิมพ์มาเลย หรือใช้ปุ่มเมนูด้านล่าง ⬇️"

     [Quick Reply: ส่งไฟล์ทดลอง / ดูไฟล์ทั้งหมด / คู่มือใช้งาน]
     ```
   - Send all 3 ใน 1 push call (LINE allows up to 5 messages/call)
   - Set `welcomed = true`
3. Attach Rich Menu (Phase 6 จะ link)

**Done criteria Phase 2:**
- [ ] User add bot → ได้ greeting + link button
- [ ] Click link → web confirm → LINE redirect → linked
- [ ] After link → welcome flow ส่ง 3 messages
- [ ] `LineUser` row populated correctly

---

### Phase 3 — File Upload Flow (~4-5 วัน)

#### Step 3.1: Implement `LineBotAdapter.download_attachment()`
1. Use `line-bot-sdk` MessagingApi to call `getMessageContent(messageId)`
2. Returns bytes + content-type (LINE doesn't provide filename for image/video — generate)
3. For `file` type: filename comes from event message.fileName

#### Step 3.2: Handle `message` events (file/image/video/audio)
1. Implement `_handle_message_file(event, line_user)`:
   - Resolve PDB user from line_user
   - Check linked? → if not, send "กรุณาเชื่อมบัญชีก่อน" + link button (reuse Step 2.1)
   - Download via adapter
   - **Show typing:** `POST /v2/bot/chat/loading/start` (fire-and-forget)
   - Reuse `bot_handlers.handle_file_upload(pdb_user_id, bytes, filename, mime_type)`:
     1. Save to `uploads/{file_id}_{filename}`
     2. Determine filetype from extension/MIME
     3. `extract_text(filepath, filetype)`
     4. `compute_content_hash(extracted_text)`
     5. `check_upload_allowed(db, user)` → if exceed → reply error Flex
     6. Insert File row
     7. **BYOS handoff:** `storage_router.push_raw_to_drive_if_byos()` (best-effort)
     8. Run `organize_new_files()` (auto)
     9. Return file_id + summary
   - Reply Flex confirmation card:
     ```
     ┌──────────────────────────┐
     │ 📄 thesis-2026.pdf       │
     │ 2.3 MB · 12 หน้า         │
     │ ✅ จัดเรียบร้อยแล้ว       │
     │ Cluster: AI Research     │
     │ Topics: deep learning... │
     │ [เปิดดู] [ขอไฟล์กลับ]    │
     └──────────────────────────┘
     ```

#### Step 3.3: Handle `message` events (URL in text)
1. Implement `_handle_message_text(event, line_user)`:
   - Detect URL pattern (regex `https?://...`)
   - If URL detected:
     - Reply: "พบลิงก์ — ต้องการให้เก็บใน PDB ไหม?" + Quick Reply [ใช่ / ไม่ใช่ ถามคำถาม]
     - On confirm → call `bot_handlers.handle_url_upload(pdb_user_id, url)` → reuse `pdb_upload_from_url` from v7.5.0
2. If no URL → fall through to chat/search (Phase 4)

#### Step 3.4: Plan limit error UX
1. ถ้า `check_upload_allowed()` raise → reply Flex:
   ```
   ⚠️ เกิน limit ของ Free plan แล้ว
   - ใช้ไป: 5/5 ไฟล์
   - Upgrade Starter: ฿199/เดือน
   [Upgrade] [ดูแผน]
   ```

**Done criteria Phase 3:**
- [ ] User send PDF → ได้ Flex card สรุปกลับใน <30 sec (or <2 min via Push)
- [ ] BYOS user → ไฟล์ขึ้น Drive อัตโนมัติ
- [ ] File ใหญ่เกิน 10MB → reply error
- [ ] User ไม่ link → reply prompt to link
- [ ] Plan limit exceed → reply upgrade prompt

---

### Phase 4 — Chat / Search / Stats (~3-4 วัน)

#### Step 4.1: Intent detection
1. Implement `bot_handlers.detect_intent(text: str) -> Intent`:
   - URL pattern → INTENT_URL_UPLOAD
   - "หา|ค้น|search|find" + keywords → INTENT_SEARCH
   - "ขอ|ให้|send" + filename → INTENT_GET_FILE
   - "กี่|จำนวน|how many|count" → INTENT_STATS
   - "สร้าง pack|create pack" → INTENT_CREATE_PACK (defer to v8.1)
   - Default → INTENT_CHAT

#### Step 4.2: Chat path
1. `handle_chat(pdb_user_id, question)`:
   - Call `chat_with_retrieval(db, user_id, question)` (existing)
   - Reply text (max 5000 chars) + Quick Reply [ถามต่อ / ดู source / ค้นหาเพิ่ม]
   - Sources → ใส่ใน Flex card secondary message (ถ้ามี ≥ 1 source)

#### Step 4.3: Search path
1. `handle_search(pdb_user_id, query)`:
   - Call `vector_search.hybrid_search(query, user_id, top_k=5)`
   - Reply Flex Carousel (max 10 cards):
     ```
     ┌──────────┐ ┌──────────┐ ┌──────────┐
     │ 📄 file1 │ │ 📄 file2 │ │ 📄 file3 │
     │ summary  │ │ summary  │ │ summary  │
     │ [เปิด]   │ │ [เปิด]   │ │ [เปิด]   │
     └──────────┘ └──────────┘ └──────────┘
     ```
   - แต่ละ card → tap "เปิด" = postback → ส่ง file detail Flex card

#### Step 4.4: Stats path
1. `handle_stats(pdb_user_id)`:
   - Query DB: file count, cluster count, pack count, storage usage
   - Reply Flex card "📊 สถานะตู้ของคุณ" (reuse builder จาก welcome flow)

#### Step 4.5: Get file path
1. `handle_get_file(pdb_user_id, filename_hint)`:
   - Search files by filename (LIKE query) — top 1
   - If found → reply Flex card + signed download URL (TTL 30 min)
     - URL = `https://pdb.app/d/{token}` ← Phase 1.3 endpoint
   - If not found → "ไม่เจอไฟล์ '{filename_hint}' — ลองค้นหาด้วย keyword?" + Quick Reply

**Done criteria Phase 4:**
- [ ] User ถาม "ฉันมีกี่ไฟล์" → ตอบ stats card
- [ ] User ถาม "หาไฟล์เกี่ยวกับ AI" → ตอบ carousel 5 cards
- [ ] User ถาม "thesis-2026.pdf" → ตอบ file card + download link
- [ ] User ถามทั่วไป (no intent) → fall through to AI chat → ตอบ
- [ ] Sources cited correctly

---

### Phase 5 — Forward File + Edge Cases (~2-3 วัน)

#### Step 5.1: Handle forwarded files
- LINE forwards = fresh `message` event ของ underlying type → already handled by Phase 3
- เพิ่ม detection: ถ้า event มี `forward` flag (ถ้า LINE send) → log + same handling
- Edge: หลายไฟล์ forward พร้อมกัน → batch process (don't reply per file, reply summary)

#### Step 5.2: Reply token expiry handling
- ถ้า `replyMessage` fail with "Invalid reply token" → fall back to `pushMessage`
- Track push count → if exceed monthly free quota (200) → log warning + alert admin
- Free tier policy: ไม่ proactive push (welcome flow ใช้ replyMessage ตอน accountLink)

#### Step 5.3: Error message UX (Flex builder)
- Standard error Flex template สำหรับ:
  - File too large (>10MB)
  - Unsupported file type
  - Plan limit exceeded
  - Server error
  - Account not linked
  - LINE not configured (admin alert)

---

### Phase 6 — Rich Menu (~2 วัน)

#### Step 6.1: Design Rich Menu image
- 2500×1686 px (LINE spec)
- 6 tiles, 3×2 grid
- Color: indigo + dark theme matching PDB
- Export as PNG → `legacy-frontend/line-rich-menu.png`

#### Step 6.2: Create Rich Menu via API
- One-time setup script: `scripts/setup_line_rich_menu.py`
  1. `POST /v2/bot/richmenu` — create menu structure (areas + actions)
  2. `POST /v2/bot/richmenu/{richMenuId}/content` — upload image
  3. `POST /v2/bot/user/all/richmenu/{richMenuId}` — set as default
- Areas (3×2):
  | Tile | Area | Action |
  |---|---|---|
  | 📤 อัพโหลด | top-left | postback `action=upload_help` |
  | 🔍 ค้นหา | top-mid | postback `action=search` |
  | 💬 ถาม AI | top-right | postback `action=chat_help` |
  | 📚 รายการ | bot-left | postback `action=list_files` |
  | ⚙️ ตั้งค่า | bot-mid | postback `action=settings` |
  | 🌐 เปิดเว็บ | bot-right | URI `https://pdb.app/app` |

#### Step 6.3: Postback handler
- Implement `_handle_postback(event, line_user)` ใน line_bot.py
- Each `action=X` → call corresponding handler in bot_handlers.py

---

### Phase 7 — Polish + Launch Prep (~2 วัน)

#### Step 7.1: Profile UI in app.html
- เพิ่ม section "🟢 LINE Bot" ใน profile modal
- Show status: linked / not linked
- Linked → show LINE display name + "ตัดการเชื่อม" button
- Not linked → show "เชื่อม LINE Bot" button → opens LINE deep link or QR

#### Step 7.2: Admin status endpoint
- `GET /api/line/status` (admin only — check via plan or specific email):
  - Total linked users
  - Today's message count
  - Push quota used / 200
  - Error rate

#### Step 7.3: Dockerfile + Fly.io secrets
- Verify `line-bot-sdk` install ใน Docker build
- `fly secrets set LINE_CHANNEL_SECRET=... LINE_CHANNEL_ACCESS_TOKEN=...`
- Test deploy on staging

#### Step 7.4: Documentation
- เพิ่ม section ใน `docs/LINE_BOT_SETUP.md`:
  - LINE Developer account setup
  - Channel creation walkthrough
  - Webhook URL config
  - Rich Menu deployment script

---

## 🧪 Test Scenarios (สำหรับฟ้า)

### Happy Path
1. User add bot → ได้ greeting + link button
2. Tap link → opens auth-line.html → login → confirm → redirect → accountLink event → welcome flow (3 msgs) → Rich Menu attached
3. User send PDF → ได้ Flex confirmation + AI summary
4. User text "หาไฟล์เรื่อง AI" → ได้ carousel 5 cards
5. User text "ฉันมีกี่ไฟล์" → ได้ stats card
6. User tap "เปิด" บน file card → reply file detail + download URL → tap → ไฟล์โหลดลง

### Validation Errors
- Invalid HMAC signature → 401 INVALID_SIGNATURE
- Empty webhook body → 400
- File >10MB → reply Flex error
- Unsupported file type (.exe) → reply Flex error
- File extraction fail → reply "ขอโทษ — ไม่สามารถอ่านไฟล์นี้ได้"

### Auth Errors
- User send message without linking → reply prompt to link
- Expired link_nonce → reply "ลิงก์หมดอายุ — กรุณาเริ่มใหม่"
- Already linked → 409 on confirm-link
- Disconnect → bot lose access (next message gets prompt)

### Edge Cases
- User unfollow then follow again → don't re-send welcome (welcomed flag)
- User forward 5 files at once → batch process
- Reply token expired → fallback to push message
- Push quota exceeded → log warning + reply with web link instead of push
- BYOS push fail → log warning, don't block ingest
- Plan limit exceeded → upgrade prompt
- Concurrent uploads same user → handled by DB transaction
- LINE userId already linked to different PDB user → reject confirm

### Performance
- Webhook ack < 1 sec (hard requirement)
- File processing background — typing indicator visible
- Reply within 30 sec (reply token validity) OR fall back to push

---

## ✅ Done Criteria

- [ ] All 7 phases implemented
- [ ] `tests/test_line_bot.py` ≥ 20 cases pass
- [ ] `scripts/line_bot_smoke.py` 100% pass (in-process)
- [ ] Real E2E manual test on Fly.io staging:
  - Add bot in LINE app (mobile)
  - Link account
  - Upload PDF, image, audio
  - Send 3 chat questions
  - Forward link from another chat
  - Get file back via download link
  - Disconnect
- [ ] No security issues: webhook signature verified, JWT secret rotated, signed URLs verified, no SSRF in URL fetch
- [ ] Memory updated:
  - `current/pipeline-state.md` → state = `done`
  - `contracts/api-spec.md` → 5 new endpoints documented
  - `project/decisions.md` → add LINE-001 (bot adapter pattern), LINE-002 (signed URL pattern)
- [ ] Convention compliance: Thai comments, English vars, JWT auth, error format
- [ ] No regression: 169/169 existing tests + ≥ 20 new = 189+ pass
- [ ] Welcome flow shown only once per user (welcomed flag works)
- [ ] Rich Menu visible on mobile LINE app
- [ ] Admin status endpoint returns correct counts

---

## ⚠️ Risks / Open Questions

### 🔴 Critical Risks
1. **Reply token 30 sec expiry vs slow LLM/extract** — long PDF extract + AI summary might take >30s
   - Mitigation: ack webhook immediately, use `pushMessage` for delayed responses
   - Trade-off: push counts against quota (200/month free)
2. **LINE Channel Access Token rotation** — token can expire / be revoked
   - Mitigation: monitor + alert; document rotation process
3. **LINE policy changes** — past examples (file size cuts, LINE Notify shutdown)
   - Mitigation: follow LINE developer changelog; design loosely-coupled adapter

### 🟡 Medium Risks
4. **Push quota 200/month exhaustion** — if user base grows
   - Mitigation: track usage; alert at 80%; upgrade Light plan (~฿1,200/mo) when needed
5. **Single LINE account → multi PDB account collision** — user uses 2 PDB accounts
   - **Open question:** Q1 below
6. **Spam abuse** — fake LINE accounts spamming uploads
   - Mitigation: rate limit per LINE userId (10 msg/min, 100 files/day)
7. **In-app browser quirks** — iOS LINE browser ≠ Safari ≠ Chrome
   - Mitigation: test all 3; provide "open in default browser" fallback

### 🟢 Low Risks
8. **Rich Menu image quality on different screen sizes** — auto-scaled by LINE
9. **Thai language detection in intent classification** — TF-IDF or simple keyword good enough for MVP

### Open Questions for User
| # | Question | แนะนำ default |
|---|---|---|
| **Q1** | 1 LINE account → 1 PDB account หรือ multi? | **1:1 unique** in MVP. Multi เลื่อน Phase 2 |
| **Q2** | Free user limit ใน LINE bot — 5 files/month ตามแผน หรือ generous กว่านี้? | **เท่า web** — `check_upload_allowed()` เดียวกัน |
| **Q3** | Welcome flow — show ทุกครั้ง re-add หรือ once-only? | **Once-only** (welcomed flag) |
| **Q4** | Push notify "organize done" — เปิด default หรือ opt-in? | **Opt-in** (ตั้งค่าใน profile) — กัน annoy |
| **Q5** | LINE Login OAuth — wire ตอน v8.0.0 เลย หรือ v8.1.0? | **v8.0.0** — ใช้ใน auth-line.html "หรือเข้าสู่ระบบด้วย LINE" |
| **Q6** | Domain — ใช้ `personaldatabank.fly.dev` หรือ custom domain? | **personaldatabank.fly.dev** ตามเดิม |
| **Q7** | Bot display name + bio | **"PDB Assistant"** + bio "ผู้ช่วยจัดการข้อมูลส่วนตัวของคุณ" |
| **Q8** | Rich menu — ใส่ logo PDB ใน image ไหม | **ใช่** — branding consistent |

---

## 📌 Notes for เขียว

### Critical gotchas
1. **Webhook MUST ack 200 within 1 sec** — ใช้ `BackgroundTasks` for slow work; ห้าม block
2. **`getMessageContent` = different host** — `api-data.line.me` ไม่ใช่ `api.line.me`
3. **Download IMMEDIATELY** — LINE retains content ~14 days only; ห้าม cache messageId
4. **Reply token = one-time use, 30 sec expiry** — ห้าม retry; ใช้ push fallback
5. **HMAC signature uses RAW body** — read `await request.body()` ก่อน parse JSON
6. **Account Link nonce ≥128 bits** — ใช้ `secrets.token_urlsafe(32)` (256 bits = safe margin)
7. **LineUser unique constraint** — `(line_user_id, pdb_user_id)` — กัน duplicate

### Best practices
- ใช้ `line-bot-sdk-python` v3 (latest) — async-friendly, has type hints
- Mock LINE API ใน tests — ใช้ `unittest.mock.patch` ที่ adapter level
- Log ทุก webhook event ใน DB (table `line_webhook_logs` อาจเพิ่มทีหลัง — start with file logs)
- Test webhook locally with **ngrok** — `ngrok http 8000` → set webhook URL ใน LINE dev console temporarily
- ใช้ FastAPI `Depends` for `line_user → pdb_user` resolver (clean code)

### File-level architectural notes
- `bot_handlers.py` = **platform-agnostic** — ห้าม import `linebot` package ที่นี่
- `bot_adapters.py` LineBotAdapter = **only place that imports linebot**
- `bot_messages.py` = pure function builders (input data → Flex JSON) — easy to unit test
- `signed_urls.py` = **shared utility** — ใช้ทั้ง LINE bot + future MCP + web sharing

### Don'ts
- ❌ ห้าม store LINE messageId in DB เกิน 1 ชั่วโมง (no use case + privacy)
- ❌ ห้าม proactive push ที่ไม่จำเป็น (waste quota + annoy user)
- ❌ ห้าม block on Drive push fail (best-effort เสมอ — ตาม STORAGE-001)
- ❌ ห้าม leak file_id ใน LINE message log
- ❌ ห้ามแตะ `.env`, `.jwt_secret`, `.mcp_secret`, `projectkey.db`

---

## 🎁 Future Phases (out of scope for v8.0.0)

- **v8.1.0 — Telegram Bot** (~1-2 weeks): reuse `bot_handlers.py` + new `TelegramBotAdapter`
- **v8.2.0 — Discord Bot** (~3-5 days): same pattern, Pycord SDK
- **v8.3.0 — LINE LIFF App** (~1 week): full webview app inside LINE — better UX than Flex limitations
- **v8.4.0 — Voice message transcription** (~1 week): integrate Whisper / Typhoon Audio for Thai
- **v8.5.0 — Push notification opt-in** (~3 days): "organize done" / weekly recap / yearly memory recall
- **v9.0.0 — Multi LINE account per PDB user** — work + personal split

---

## 📊 Success Metrics (post-launch)

- **Activation:** % linked users / total bot adds (target ≥ 60%)
- **Engagement:** avg messages/user/week (target ≥ 5)
- **File ingestion:** files uploaded via LINE / total files (target ≥ 30%)
- **Latency:** avg reply time for chat (target < 5 sec p50, < 15 sec p95)
- **Reliability:** webhook success rate (target ≥ 99.5%)
- **Conversion:** Free → Pro conversion (target ≥ 5% of active LINE users)

---

**End of plan.** รอ user approve ก่อน update pipeline-state → `plan_approved` → ส่งต่อให้เขียว
