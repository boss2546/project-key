# 🟢 Fix Plan: เขียว-A — Security + DB + Backend API

> **Created:** 2026-05-17 · **Author:** ผม (in coordination with user)
> **Target version:** v10.1.0 (cumulative through sprints) · **Pipeline:** 4 sprints · ~3.5 weeks full-time

---

## 🎯 Mission Statement

ปิดรู **security** ที่ทำให้ระบบไม่พร้อม public launch + แก้ **API contract** ที่ขาดมาตรฐาน + แก้ **DB integrity** ที่ทำให้ข้อมูลเสียหายได้

เจ้าหน้าที่: เขียว-A (คุณ) — รับผิดชอบ backend core, security, DB, API
ทำงาน **คู่ขนาน** กับ เขียว-B (Perf + Thai + Frontend + Ops) แต่ **คนละไฟล์**

---

## 📋 Pipeline State Header

```yaml
plan_id: fix-plan-เขียว-A
sprint_count: 4 (Sprint 0, 1, 2, 3)
milestones: 28 (A0.1-A0.5, A1.1-A1.10, A2.1-A2.7, A3.1-A3.6)
parallel_with: เขียว-B
review_gate: ฟ้า (review หลัง sprint end + final UI test)
target_p0_closure: ทั้งหมดที่อยู่ใน scope (24/24)
estimated_effort: 16 sprint-days
```

---

## 🗂 Scope: Files Owned

### ✅ เขียว-A เป็นเจ้าของ (แตะได้คนเดียว)

```
backend/main.py           # ⚠️ MEGA-FILE 5570 LOC — ระวัง merge conflict
backend/auth.py
backend/admin.py
backend/database.py       # Schema + migrations
backend/config.py         # ❗ B request changes via inbox
backend/llm.py            # LLM API client + validation
backend/line_quota.py     # Rate limit utilities (existing)

# Test files (สร้างใหม่)
backend/_test_auth.py
backend/_test_endpoints.py
backend/_test_database.py
backend/_test_config.py
backend/_test_llm.py      # (มีอยู่แล้ว — A เพิ่ม schema validation tests)

# Schema modules (สร้างใหม่)
backend/schemas/__init__.py
backend/schemas/user.py
backend/schemas/file.py
backend/schemas/cluster.py
backend/schemas/error.py
backend/schemas/admin.py

# Migration framework (สร้างใหม่ตอน A3.5)
backend/migrations/__init__.py
backend/migrations/0001_*.py
```

### ❌ เขียว-A ห้ามแตะ (เป็นของ B)

```
backend/vector_search.py
backend/duplicate_detector.py
backend/extraction.py
backend/organizer.py
backend/upload_worker.py
backend/progress_tracker.py
backend/shared_links.py
backend/drive_oauth.py
backend/embeddings.py
backend/ai_ingest.py
backend/retriever.py
backend/processors/*
legacy-frontend/*
Dockerfile
fly.toml
pyproject.toml
.github/workflows/*
requirements-fly.txt
scripts/*
```

### 🤝 จุดประสาน (ทั้งคู่ต้องคุย)

```
backend/config.py    — A owns, B requests via inbox
backend/main.py      — A owns เต็มไฟล์, แต่ B อาจขอแก้ specific helper
                       (เช่น เพิ่ม middleware ใหม่) — ผ่าน inbox เสมอ
backend/llm.py       — A defines API contract, B uses
```

---

## 🚦 Rules of Engagement (ห้ามฝ่าฝืน)

1. **1 branch per sprint**: `fix/A-sprint-0`, `fix/A-sprint-1`, etc.
2. **Commit tag**: ทุก commit message ขึ้นต้น `[A0.X]` หรือ `[A1.X]` ตาม milestone
3. **Co-Authored-By footer**: ใส่ทุก commit
4. **No force push** บน sprint branch หลัง push แล้ว
5. **Deploy gate**: ห้าม deploy prod กลาง sprint — รวบทุก milestone end of sprint deploy ครั้งเดียว ยกเว้น A0.1 (security emergency)
6. **Migration rule**: ทุก ALTER TABLE → backup DB ก่อน + try/except + idempotent
7. **Backwards compat**: ทุก API change ต้อง support legacy path 30 วัน
8. **Test first, then code**: เขียน test ก่อน implement (TDD where reasonable)
9. **Inbox protocol**: ขอ B แก้ไฟล์ของ B → เขียน `.agent-memory/communication/inbox/for-เขียว-B.md`
10. **Pre-merge**: ทุก sprint end ส่ง ฟ้า review ก่อน merge

---

## 📅 Sprint Roadmap Overview

| Sprint | Theme | Days | Milestones | Deploy |
|--------|-------|-----:|-----------|:------:|
| **0** | Stop the Bleeding | 1 | A0.1-A0.5 | ✅ Day 1 emergency |
| **1** | API Contract + DB | 5 | A1.1-A1.10 | ✅ Day 6 |
| **2** | Auth + Rate Limit + LLM safety | 5 | A2.1-A2.7 | ✅ Day 11 |
| **3** | Tests + Refactor + Cleanup | 5 | A3.1-A3.6 | ✅ Day 16 (final) |

---

# 🚨 Sprint 0 — Stop the Bleeding (Day 1)

**Goal:** ปิดรู security ที่อันตรายที่สุดใน 4-6 ชม. · deploy ทันทีถ้าเสร็จ

---

## A0.1 — Rotate ALL Secrets + Clean Git History

### What
- เปลี่ยน secret ทั้งหมดที่หลุดอยู่ใน `.env` (อยู่ใน git history แล้ว — public risk)
- ลบ `.env` จาก git history ด้วย `git filter-repo`
- เพิ่ม `.env` ใน `.gitignore` (ถ้ายังไม่ใส่)
- เพิ่ม pre-commit hook (B จะทำใน Sprint 3)

### Why
- Secret เหล่านี้ public ใน git ตลอดเวลา — เปลี่ยน Fly secret อย่างเดียวไม่พอ
- ทุก commit history ยังมีค่าเดิม → ใครก็เอาไปใช้ได้

### How (Steps)

```bash
# 1. List secrets ที่ต้อง rotate
echo "Rotating:"
echo "- OPENROUTER_API_KEY (sk-or-v1-...)"
echo "- STRIPE_SECRET_KEY (sk_test_... — even test keys, leaked = bad)"
echo "- GOOGLE_OAUTH_CLIENT_SECRET (GOCSPX-...)"
echo "- GOOGLE_PICKER_API_KEY (AIzaSy...)"
echo "- LLAMA_CLOUD_API_KEY (llx-...)"
echo "- GOOGLE_API_KEY (อาจหลุดเข้า .env ตอนทดสอบ)"
echo "- JWT_SECRET_KEY (ถ้าไม่เคย rotate)"
echo "- MCP_SECRET (ถ้าไม่เคย rotate)"

# 2. ไปแต่ละ console แล้ว revoke + สร้างใหม่
# - openrouter.ai/keys
# - dashboard.stripe.com/apikeys
# - console.cloud.google.com (OAuth + Picker + Generative AI)
# - cloud.llamaindex.ai

# 3. เก็บค่าใหม่ใน Fly secrets
flyctl secrets set OPENROUTER_API_KEY=<new> -a personaldatabank
flyctl secrets set STRIPE_SECRET_KEY=<new> -a personaldatabank
flyctl secrets set GOOGLE_OAUTH_CLIENT_SECRET=<new> -a personaldatabank
flyctl secrets set GOOGLE_PICKER_API_KEY=<new> -a personaldatabank
flyctl secrets set LLAMA_CLOUD_API_KEY=<new> -a personaldatabank
flyctl secrets set GOOGLE_API_KEY=<new> -a personaldatabank

# 4. ลบ .env จาก git history (DESTRUCTIVE — backup ก่อน)
cp -r .git ../PDB-git-backup
git filter-repo --invert-paths --path .env --force
# OR if filter-repo not installed:
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch .env" --prune-empty --tag-name-filter cat -- --all

# 5. Force push (ครั้งเดียว) + แจ้ง collaborators
git push --force --all origin
git push --force --tags origin

# 6. Verify .env not in history
git log --all --oneline -- .env  # should return nothing
```

### Test (Acceptance Gate)

```bash
# Smoke test ทุก service
curl https://personaldatabank.fly.dev/health
# → 200 {"ok":true,"version":"..."}

# Login (verify JWT_SECRET ยังใช้ได้)
curl -X POST .../api/auth/login -d '{"email":"...","password":"..."}'
# → 200 + valid token

# LLM call ผ่าน chat
curl -X POST .../api/chat -H "Authorization: Bearer $TOKEN" -d '{"question":"hello"}'
# → 200 + AI response (no 401/403 from key)

# Drive OAuth init
curl .../api/drive/oauth/init -H "Authorization: Bearer $TOKEN"
# → 200 + redirect URL

# LINE webhook (ถ้าใช้)
# ส่ง test message via LINE Console webhook tester → 200

# Verify git
git log --all -- .env  # empty
```

### Rollback

- ถ้า service ใดพังหลัง rotate → revert Fly secret ไป old value (เก็บไว้ใน password manager 24h overlap)
- ถ้า git filter-repo เสีย local repo → restore `../PDB-git-backup`
- **Warning:** force push history ย้อนกลับยาก — แจ้ง collaborators ก่อนทำ

### Files Touched

```
.env                     (DELETE from working dir + history)
.gitignore               (verify .env in)
Fly secrets              (rotate ทุก key)
+ external services      (revoke + create new keys)
```

### Time Estimate: 2-3 hours

---

## A0.2 — Enable `PRAGMA foreign_keys=ON`

### What
SQLite default ปิด FK enforcement → schema มี FK column แต่ไม่มีคนตรวจ
เปิดให้ ON ตอน init_db เพื่อให้ ON DELETE CASCADE ทำงาน (เซ็ตใน A1.8)

### Why
ปัจจุบันถ้าลบ User → File rows ของ user **ไม่ถูกลบ** = orphan rows ใน DB

### How

```python
# backend/database.py
# ใน init_db() หาบรรทัดที่ตั้ง WAL → เพิ่มตรงนั้น

async def init_db():
    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA foreign_keys=ON"))  # ⬅ เพิ่ม
        # ... rest of init
```

**สำคัญ:** PRAGMA foreign_keys ต้องตั้ง **ต่อ connection** — ถ้าใช้ connection pool ต้องตั้งทุก connection
อาจต้องใช้ SQLAlchemy event listener:

```python
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
```

### Test

```python
# backend/_test_database.py
async def test_foreign_keys_enabled(db_session):
    result = await db_session.execute(text("PRAGMA foreign_keys"))
    assert result.scalar() == 1, "FK enforcement off!"

async def test_fk_cascade_works(db_session):
    """หลัง A1.8 cascade ตั้งแล้วต้อง pass"""
    user = User(email="test@x.com", ...)
    db_session.add(user)
    await db_session.commit()
    
    file = File(user_id=user.id, ...)
    db_session.add(file)
    await db_session.commit()
    
    await db_session.delete(user)
    await db_session.commit()
    
    # File row ต้องหายอัตโนมัติ (หลัง A1.8 set cascade)
    result = await db_session.execute(select(File).where(File.id == file.id))
    assert result.scalar_one_or_none() is None
```

### Rollback
ลบ event listener + ลบ PRAGMA line → connection กลับ default behavior

### Files Touched
```
backend/database.py        (~3-5 บรรทัด)
backend/_test_database.py  (สร้างใหม่)
```

### Time Estimate: 30 นาที

---

## A0.3 — Drop `plaintext_password` Column

### What
ลบ column `users.plaintext_password` + flag `ALLOW_ADMIN_VIEW_PASSWORD` + admin view-password endpoint

### Why
- DB leak = รหัสผ่านทุก user หลุดเป็น plaintext
- ผิดกฎหมาย PDPA/GDPR
- comment ในโค้ดบอกเองว่า "must DROP before public launch"

### How (3 phases — ห้ามรวบ)

**Phase 1: Stop writing** (deploy ทันที)
```python
# backend/auth.py:128 — ลบบรรทัด
# OLD: plaintext_password=password if _ALLOW_VIEW_PWD else None
# NEW: (ลบทิ้ง)
```

**Phase 2: Stop reading** (deploy ทันที)
```python
# backend/admin.py:507-510 — ลบ endpoint admin_view_password
# backend/main.py:2281-2299 — ลบ /api/admin/users/{user_id}/password endpoint

# backend/config.py:198 — ลบ ALLOW_ADMIN_VIEW_PASSWORD constant
```

**Phase 3: Drop column** (รอ Phase 1+2 deploy ผ่าน 24h ก่อนทำ)
```python
# backend/database.py — ใน init_db() เพิ่ม migration block
try:
    await conn.execute(text("ALTER TABLE users DROP COLUMN plaintext_password"))
except Exception as e:
    # SQLite 3.35+ supports DROP COLUMN; ถ้า fail = table rebuild pattern
    logger.warning(f"DROP COLUMN failed (probably already dropped): {e}")

# OR ถ้า SQLite version เก่า → table rebuild:
# 1. CREATE TABLE users_new (without plaintext_password)
# 2. INSERT INTO users_new SELECT (all cols except plaintext_password) FROM users
# 3. DROP TABLE users
# 4. ALTER TABLE users_new RENAME TO users
```

### Test

```python
# backend/_test_auth.py
async def test_no_plaintext_password_on_register(client, db_session):
    response = await client.post("/api/auth/register", json={
        "email": "test@x.com", "password": "Secret123"
    })
    assert response.status_code in (200, 201)
    
    user = (await db_session.execute(
        select(User).where(User.email == "test@x.com")
    )).scalar_one()
    
    # ห้ามมี attribute หรือถ้ามีต้องเป็น None
    plaintext = getattr(user, "plaintext_password", None)
    assert plaintext is None or plaintext == ""

async def test_admin_view_password_endpoint_gone(client, admin_token):
    response = await client.get(
        "/api/admin/users/some-id/password",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 404  # endpoint ถูกลบ

# backend/_test_database.py
async def test_no_plaintext_password_column(db_session):
    result = await db_session.execute(text("PRAGMA table_info(users)"))
    columns = [row[1] for row in result.fetchall()]
    assert "plaintext_password" not in columns
```

### Rollback (เฉพาะ Phase 3)
- Restore DB จาก backup (pre-migration)
- Phase 1+2 rollback แค่ revert commit ก็พอ

### Files Touched
```
backend/auth.py          (-1 line)
backend/admin.py         (-30 lines: ลบ endpoint)
backend/main.py          (-20 lines: ลบ endpoint)
backend/config.py        (-3 lines: ลบ ALLOW_ADMIN_VIEW_PASSWORD)
backend/database.py      (+5 lines: migration block)
backend/_test_auth.py    (+10 lines tests)
```

### Time Estimate: 1 hour

---

## A0.4 — JWT Secret Env Var Enforce (Fail-Hard ใน Fly)

### What
ถ้ารันบน Fly.io (detect via `/app/data`) แล้ว `JWT_SECRET_KEY` env ไม่ตั้ง → **ปฏิเสธ start** (fail-hard)
Dev local ยัง fallback ไป `.jwt_secret` file ได้ตามเดิม

### Why
Multi-machine Fly scale = แต่ละเครื่อง generate JWT secret ของตัวเอง = user JWT พังสลับเครื่อง
ปัจจุบัน warn เฉย ไม่ enforce

### How

```python
# backend/config.py:144-181 — แก้ logic

_jwt_env = os.getenv("JWT_SECRET_KEY")
_running_on_fly = os.path.isdir("/app/data")

if _running_on_fly and not _jwt_env:
    print(
        "FATAL: JWT_SECRET_KEY env var required when running on Fly.io.\n"
        "  File-based fallback (.jwt_secret) breaks multi-machine scale.\n"
        "  Fix: flyctl secrets set JWT_SECRET_KEY=$(openssl rand -base64 64) -a personaldatabank",
        file=sys.stderr,
    )
    sys.exit(1)

JWT_SECRET_KEY = _jwt_env or _generate_jwt_secret()
```

### Test

```python
# backend/_test_config.py
def test_jwt_fails_hard_on_fly_no_env(monkeypatch, tmp_path):
    # mock /app/data exists
    monkeypatch.setattr(os.path, "isdir", lambda p: p == "/app/data")
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    
    with pytest.raises(SystemExit):
        import importlib
        import backend.config
        importlib.reload(backend.config)

def test_jwt_works_local_no_env(monkeypatch, tmp_path):
    monkeypatch.setattr(os.path, "isdir", lambda p: False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    
    import importlib
    import backend.config
    importlib.reload(backend.config)
    
    assert backend.config.JWT_SECRET_KEY  # generated to file ok

def test_jwt_uses_env_var(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-12345")
    import importlib
    import backend.config
    importlib.reload(backend.config)
    
    assert backend.config.JWT_SECRET_KEY == "test-secret-12345"
```

### Rollback
revert commit → กลับเป็น warn-only behavior

### Files Touched
```
backend/config.py          (~15 lines)
backend/_test_config.py    (สร้างใหม่ ~30 lines)
```

### Pre-deploy Check
```bash
# Verify Fly secret already set ก่อน deploy commit นี้
flyctl secrets list -a personaldatabank | grep JWT_SECRET_KEY
# ถ้าไม่มี → ตั้งก่อน deploy code นี้
flyctl secrets set JWT_SECRET_KEY=$(openssl rand -base64 64) -a personaldatabank --stage
```

### Time Estimate: 45 นาที

---

## A0.5 — `ADMIN_PASSWORD` Soft Fail (No sys.exit)

### What
เปลี่ยน `sys.exit(1)` → warn + disable admin endpoints (return 503 ถ้าใครเรียก)

### Why
`ADMIN_PASSWORD` env หาย = ทั้ง app ดับ = user ทั้งหมด out of service เพราะ feature เดียวที่ใช้คือ admin override

### How

```python
# backend/config.py:188-196

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
if not ADMIN_PASSWORD:
    import sys
    print(
        "WARN: ADMIN_PASSWORD env var not set. "
        "Admin override endpoints will return 503. "
        "App continues serving regular users. "
        "Set via: flyctl secrets set ADMIN_PASSWORD=... -a personaldatabank",
        file=sys.stderr,
    )

# Helper สำหรับ endpoint ใช้
def is_admin_password_configured() -> bool:
    return bool(ADMIN_PASSWORD)

# backend/main.py — ใน admin override check
if not is_admin_password_configured():
    raise HTTPException(503, detail={"error": {"code": "ADMIN_UNAVAILABLE", "message": "Admin features not configured"}})
```

### Test

```python
# backend/_test_config.py
def test_no_admin_password_warns_not_crashes(monkeypatch, capsys):
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    
    import importlib
    import backend.config
    importlib.reload(backend.config)  # ไม่ throw
    
    captured = capsys.readouterr()
    assert "WARN" in captured.err
    assert backend.config.ADMIN_PASSWORD == ""
    assert backend.config.is_admin_password_configured() is False

# backend/_test_endpoints.py
async def test_admin_override_503_when_no_password(client, monkeypatch):
    monkeypatch.setattr("backend.config.ADMIN_PASSWORD", "")
    response = await client.post("/api/mcp/tools/call", json={...})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ADMIN_UNAVAILABLE"
```

### Rollback
revert commit

### Files Touched
```
backend/config.py     (~10 lines)
backend/main.py       (~5 lines for guard)
backend/_test_config.py + _test_endpoints.py
```

### Time Estimate: 45 นาที

---

## ✅ Sprint 0 Acceptance Gate

ก่อน close Sprint 0:
1. [ ] Secrets ทั้งหมด rotated + verified (A0.1 smoke pass)
2. [ ] `.env` หายจาก git history (`git log --all -- .env` empty)
3. [ ] `PRAGMA foreign_keys=ON` confirmed via `_test_database.py`
4. [ ] `plaintext_password` column ไม่อยู่ใน DB
5. [ ] JWT secret missing on Fly → app refuse to start
6. [ ] ADMIN_PASSWORD missing → app starts + admin endpoints 503
7. [ ] Deploy to prod + `/health` = 200 + version bump = `10.0.30-sprint0`
8. [ ] **ส่งฟ้า review** ผ่าน `for-ฟ้า.md` (security smoke test plan)
9. [ ] ฟ้า verdict = APPROVED → close Sprint 0

---

# 🛠 Sprint 1 — API Contract + DB Performance (Days 2-6)

**Goal:** สร้าง consistent API contract + แก้ DB perf ที่ทำให้ระบบช้า/พังที่ scale

---

## A1.1 — Unified Error Handler

### What
สร้าง central exception handler ที่:
- จับ `HTTPException` + `RequestValidationError` + `Exception` (catch-all)
- คืน shape เดียวกัน: `{"error": {"code": "ERR_CODE", "message": "human readable"}}`
- Log full trace server-side พร้อม `request_id`
- ลบทุก `raise HTTPException(500, detail=str(e))` ใน main.py (~14 ตำแหน่ง)

### Why
- 14 endpoints leak Python stack trace → info disclosure
- Frontend ตอนนี้เจอ error 3 รูปแบบ → ต้องเดา

### How

**Step 1: สร้าง error schema**

```python
# backend/schemas/error.py (NEW)
from pydantic import BaseModel

class ErrorDetail(BaseModel):
    code: str          # ERR_*, e.g., "ERR_FILE_NOT_FOUND"
    message: str       # human readable (TH default, EN if Accept-Language en)
    request_id: str | None = None
    details: dict | None = None  # optional extra context

class ErrorResponse(BaseModel):
    error: ErrorDetail

# Common error codes
ERR_INTERNAL = "ERR_INTERNAL"
ERR_NOT_FOUND = "ERR_NOT_FOUND"
ERR_FORBIDDEN = "ERR_FORBIDDEN"
ERR_VALIDATION = "ERR_VALIDATION"
ERR_RATE_LIMITED = "ERR_RATE_LIMITED"
ERR_QUOTA_EXCEEDED = "ERR_QUOTA_EXCEEDED"
# ... ขยาย
```

**Step 2: Middleware สำหรับ request_id**

```python
# backend/main.py
import uuid
from contextvars import ContextVar

_request_id_var: ContextVar[str] = ContextVar("request_id", default="")

@app.middleware("http")
async def request_id_middleware(request, call_next):
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:12]
    _request_id_var.set(rid)
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response
```

**Step 3: Unified handler**

```python
# backend/main.py:83-112 — replace existing
from fastapi.exceptions import RequestValidationError
from backend.schemas.error import ErrorResponse, ErrorDetail, ERR_INTERNAL, ERR_VALIDATION

@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    # ถ้า detail เป็น dict ที่มี error key อยู่แล้ว = pass through
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    
    # ถ้า detail เป็น string = wrap
    code_map = {
        400: "ERR_BAD_REQUEST", 401: "ERR_UNAUTHORIZED", 403: "ERR_FORBIDDEN",
        404: "ERR_NOT_FOUND", 409: "ERR_CONFLICT", 422: "ERR_VALIDATION",
        429: "ERR_RATE_LIMITED", 503: "ERR_UNAVAILABLE",
    }
    code = code_map.get(exc.status_code, "ERR_HTTP")
    message = str(exc.detail) if exc.detail else "An error occurred"
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": message, "request_id": _request_id_var.get()}},
        headers=exc.headers,
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": {
            "code": ERR_VALIDATION,
            "message": "Request validation failed",
            "request_id": _request_id_var.get(),
            "details": {"errors": exc.errors()},
        }},
    )

@app.exception_handler(Exception)
async def catch_all_exception_handler(request: Request, exc: Exception):
    rid = _request_id_var.get()
    logger.exception(f"[{rid}] Unhandled exception on {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"error": {
            "code": ERR_INTERNAL,
            "message": "Internal server error. Please contact support with request_id.",
            "request_id": rid,
        }},
    )
```

**Step 4: Sweep `str(e)` 14 ที่**

```python
# Replace pattern:
# OLD:
except Exception as e:
    logger.error(f"X failed: {e}")
    raise HTTPException(status_code=500, detail=str(e))

# NEW:
except Exception as e:
    logger.exception("X failed")  # logs full trace
    raise HTTPException(
        status_code=500,
        detail={"error": {"code": "ERR_X_FAILED", "message": "X operation failed"}},
    )
# OR (cleaner) — ปล่อยให้ catch-all handler จัดการ:
except Exception:
    logger.exception("X failed")
    raise  # ปล่อย exception bubble up → handler จัด format ให้
```

### Test

```python
# backend/_test_endpoints.py
async def test_500_returns_unified_error_shape(client, monkeypatch):
    # Mock endpoint to raise
    monkeypatch.setattr("backend.organizer.organize_files", lambda *a, **k: 1/0)
    
    response = await client.post("/api/organize", headers={"Authorization": f"Bearer {TOKEN}"})
    assert response.status_code == 500
    body = response.json()
    assert "error" in body
    assert "code" in body["error"]
    assert "message" in body["error"]
    assert "request_id" in body["error"]
    assert "ZeroDivisionError" not in body["error"]["message"]  # ไม่หลุด Python info

async def test_request_id_propagated(client):
    response = await client.get("/health", headers={"X-Request-ID": "test-123"})
    assert response.headers["X-Request-ID"] == "test-123"

async def test_validation_error_shape(client):
    response = await client.post("/api/auth/login", json={"email": "not-an-email"})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "ERR_VALIDATION"
    assert "details" in body["error"]
```

### Files Touched
```
backend/schemas/__init__.py    (new)
backend/schemas/error.py       (new ~50 lines)
backend/main.py                (~80 lines: middleware + handlers + ~14 sweep sites)
backend/_test_endpoints.py     (+30 lines)
```

### Time Estimate: 4-6 hours

---

## A1.2 — `response_model` for 65+ Endpoints

### What
สร้าง Pydantic response schemas + ผูกกับ endpoint ทุกตัว

### Why
- ปัจจุบัน 0 endpoints มี `response_model` → no schema validation, no OpenAPI doc, frontend ต้องเดา
- ป้องกัน sensitive field leak (mcp_secret, hashes) ผ่าน schema

### How (Phased Approach)

**Phase 1: สร้าง schema modules**

```python
# backend/schemas/user.py
from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserPublic(BaseModel):
    """Public user info — ปลอดภัยส่งให้ frontend"""
    id: str
    email: EmailStr
    name: str
    plan: str
    avatar_url: str | None = None
    created_at: datetime
    # ❌ NO password_hash, mcp_secret, jwt-related fields

class MeResponse(UserPublic):
    """/api/me — includes some extra non-sensitive fields"""
    profile_set: bool
    files_count: int
    # ❌ NO mcp_secret (เคยมี — A1.3 ลบ)

# backend/schemas/file.py
class FilePublic(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    processing_status: str
    created_at: datetime
    # ... etc

class FileListResponse(BaseModel):
    items: list[FilePublic]
    next_cursor: str | None
    has_more: bool

# (และอื่นๆ — cluster, audit, admin, MCP tool, etc.)
```

**Phase 2: ทยอย apply ทีละ endpoint group** (~5 endpoints/day)

```python
# main.py
@app.get("/api/me", response_model=MeResponse)
async def api_me(current_user: User = Depends(get_current_user), ...):
    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        # ... explicit field mapping (no **user.__dict__)
    )

@app.get("/api/files", response_model=FileListResponse)
async def api_files(...):
    return FileListResponse(items=[...], next_cursor=..., has_more=...)
```

### Test

```python
# backend/_test_endpoints.py
async def test_me_no_sensitive_fields(client, user_token):
    response = await client.get("/api/me", headers={"Authorization": f"Bearer {user_token}"})
    body = response.json()
    
    # ห้ามมี sensitive fields
    forbidden = ["password_hash", "mcp_secret", "jwt_secret", "plaintext_password"]
    for field in forbidden:
        assert field not in body, f"{field} leaked in /api/me response!"

async def test_openapi_has_schemas(client):
    response = await client.get("/openapi.json")
    schema = response.json()
    
    # Verify response_model declared
    paths = schema.get("paths", {})
    me_response = paths.get("/api/me", {}).get("get", {}).get("responses", {}).get("200", {})
    assert "content" in me_response
    assert "application/json" in me_response["content"]
    assert "schema" in me_response["content"]["application/json"]
```

### Files Touched
```
backend/schemas/user.py        (new)
backend/schemas/file.py        (new)
backend/schemas/cluster.py     (new)
backend/schemas/admin.py       (new)
backend/schemas/chat.py        (new)
backend/main.py                (~200 lines: add response_model to 65+ endpoints)
backend/admin.py               (~50 lines)
backend/auth.py                (~30 lines)
backend/_test_endpoints.py     (+100 lines coverage)
```

### Time Estimate: 2 days (ทำทีละ endpoint group)

---

## A1.3 — ลบ `mcp_secret` จาก `/api/me`

### What
ลบ field `mcp_secret` จาก response `/api/me` (และทุก response ที่ leak)

### Why
Auth credential → log/cache เก็บได้ → leak risk

### How

```python
# backend/main.py:311 — ก่อน
return {
    ...
    "mcp_secret": current_user.mcp_secret,  # ❌
    ...
}

# หลัง
return MeResponse(...)  # schema ไม่มี mcp_secret field

# ถ้า frontend ต้องใช้ mcp_secret → endpoint แยก /api/mcp/credentials (require fresh auth)
@app.get("/api/mcp/credentials", response_model=MCPCredentials)
async def api_mcp_credentials(
    current_user: User = Depends(get_current_user),
    fresh_password: str = Body(..., embed=True),  # require password re-entry
):
    if not verify_password(fresh_password, current_user.password_hash):
        raise HTTPException(401, detail={"error": {"code": "ERR_REAUTH_REQUIRED", "message": "Password required"}})
    return MCPCredentials(secret=current_user.mcp_secret)
```

### Test

```python
async def test_me_no_mcp_secret(client, user_token):
    response = await client.get("/api/me", headers={"Authorization": f"Bearer {user_token}"})
    assert "mcp_secret" not in response.json()

async def test_mcp_credentials_requires_reauth(client, user_token):
    response = await client.get(
        "/api/mcp/credentials",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"fresh_password": "wrong"}
    )
    assert response.status_code == 401
```

### Files Touched
```
backend/main.py            (~10 lines)
backend/schemas/user.py    (MeResponse no mcp_secret)
backend/_test_endpoints.py (+10 lines)
```

### Frontend Impact
Frontend ที่เคยเรียก `/api/me` แล้วเอา `.mcp_secret` ไปแสดงต้อง:
- เปลี่ยนเป็นเรียก `/api/mcp/credentials` พร้อม password
- **แจ้ง B ผ่าน inbox** เพราะ frontend อยู่ใน scope B

### Time Estimate: 1 hour

---

## A1.4 — MCP Test Endpoint → 401 (Not 200)

### What
`POST /api/mcp/test` ตอน auth fail → คืน 200 OK กับ `{"status":"error"}`
แก้เป็น raise HTTPException(401)

### Why
HTTP client / cache จะถือเป็น success → error handling ผิด

### How

```python
# backend/main.py:4791
# OLD:
if not authorization or not authorization.startswith("Bearer "):
    return {"status": "error", "message": "Missing or invalid Authorization header"}

# NEW:
if not authorization or not authorization.startswith("Bearer "):
    raise HTTPException(
        status_code=401,
        detail={"error": {"code": "ERR_UNAUTHORIZED", "message": "Missing or invalid Authorization header"}},
    )
```

### Test

```python
async def test_mcp_test_endpoint_401_on_no_auth(client):
    response = await client.post("/api/mcp/test")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ERR_UNAUTHORIZED"
```

### Time Estimate: 15 นาที

---

## A1.5 — Pagination on 4 Heavy Endpoints

### What
เพิ่ม cursor-based pagination + LIMIT บน:
- `GET /api/files`
- `GET /api/clusters`
- `POST /api/export` (อย่างน้อย chunked)
- `DELETE /api/account` (process in batches)

### Why
User 10K+ files → load all = memory ระเบิด, timeout

### How (Cursor-based pattern)

```python
# backend/main.py:1732
@app.get("/api/files", response_model=FileListResponse)
async def api_files(
    cursor: str | None = Query(None, description="Pagination cursor (opaque)"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # cursor format: base64(created_at|id) for stability
    where_clauses = [File.user_id == current_user.id]
    if cursor:
        try:
            decoded = base64.urlsafe_b64decode(cursor).decode()
            cursor_created_at, cursor_id = decoded.split("|", 1)
            where_clauses.append(
                or_(
                    File.created_at < datetime.fromisoformat(cursor_created_at),
                    and_(File.created_at == datetime.fromisoformat(cursor_created_at), File.id < cursor_id),
                )
            )
        except (ValueError, binascii.Error):
            raise HTTPException(400, detail={"error": {"code": "ERR_BAD_CURSOR", "message": "Invalid cursor"}})
    
    rows = (await db.execute(
        select(File)
        .where(*where_clauses)
        .order_by(File.created_at.desc(), File.id.desc())
        .limit(limit + 1)  # +1 to detect has_more
    )).scalars().all()
    
    has_more = len(rows) > limit
    items = rows[:limit]
    
    next_cursor = None
    if has_more and items:
        last = items[-1]
        next_cursor = base64.urlsafe_b64encode(f"{last.created_at.isoformat()}|{last.id}".encode()).decode()
    
    return FileListResponse(
        items=[FilePublic.from_orm(f) for f in items],
        next_cursor=next_cursor,
        has_more=has_more,
    )
```

**For `/api/export`** — stream chunked:

```python
@app.post("/api/export")
async def api_export(...) -> StreamingResponse:
    async def generate():
        yield '{"files":['
        first = True
        async for batch in _stream_files_in_batches(db, current_user.id, batch_size=100):
            for f in batch:
                if not first:
                    yield ","
                yield FilePublic.from_orm(f).json()
                first = False
        yield '],"clusters":[...],"context_packs":[...]}'
    
    return StreamingResponse(generate(), media_type="application/json")
```

**For `DELETE /api/account`** — batch delete with commit checkpoints:

```python
@app.delete("/api/account")
async def api_delete_account(...):
    BATCH = 500
    while True:
        deleted = (await db.execute(
            delete(File).where(File.user_id == current_user.id).limit(BATCH)
        )).rowcount
        await db.commit()
        if deleted < BATCH:
            break
    # ... repeat สำหรับ clusters, packs, etc.
    
    await db.delete(current_user)
    await db.commit()
```

### Test

```python
async def test_files_pagination(client, user_token, db_session):
    # Seed 120 files
    for i in range(120):
        db_session.add(File(user_id=user.id, filename=f"f{i}.txt", ...))
    await db_session.commit()
    
    # First page
    r1 = await client.get("/api/files", headers={"Authorization": f"Bearer {user_token}"})
    body1 = r1.json()
    assert len(body1["items"]) == 50
    assert body1["has_more"] is True
    assert body1["next_cursor"] is not None
    
    # Second page
    r2 = await client.get(f"/api/files?cursor={body1['next_cursor']}", headers={...})
    body2 = r2.json()
    assert len(body2["items"]) == 50
    assert body1["items"][0]["id"] != body2["items"][0]["id"]  # different page
    
    # Third page
    r3 = await client.get(f"/api/files?cursor={body2['next_cursor']}", headers={...})
    body3 = r3.json()
    assert len(body3["items"]) == 20
    assert body3["has_more"] is False

async def test_export_streams_large_dataset(client, user_token):
    # Seed 5000 files
    # Export should complete in <30s + not OOM
    response = await client.post("/api/export", headers={...})
    assert response.status_code == 200
    body = response.text
    assert len(body) > 100_000  # non-trivial
```

### Files Touched
```
backend/main.py            (~150 lines: 4 endpoints)
backend/schemas/file.py    (FileListResponse, etc.)
backend/_test_endpoints.py (+50 lines)
```

### Frontend Impact
Frontend ต้อง handle `next_cursor` — **แจ้ง B**

### Time Estimate: 1.5 days

---

## A1.6 — Fix N+1 in Admin Audit Log

### What
แทน loop 50 queries → 1 JOIN

### How

```python
# backend/admin.py:1015-1033
# OLD (N+1):
rows = (await db.execute(select(AuditLog).limit(50))).scalars().all()
email_cache: dict[str, str | None] = {}
for r in rows:
    if r.user_id not in email_cache:
        email_cache[r.user_id] = (await db.execute(
            select(User.email).where(User.id == r.user_id)
        )).scalar_one_or_none()
    r.user_email = email_cache[r.user_id]

# NEW (1 JOIN):
result = await db.execute(
    select(AuditLog, User.email)
    .outerjoin(User, User.id == AuditLog.user_id)
    .order_by(AuditLog.created_at.desc())
    .limit(50)
)
rows = [{"log": log, "email": email} for log, email in result.all()]
```

### Test

```python
async def test_audit_log_no_n_plus_one(client, admin_token, db_session):
    # Seed 50 audit logs with 30 unique users
    ...
    
    # Track query count
    queries_executed = []
    @event.listens_for(db_session.bind, "before_cursor_execute")
    def count_queries(*args, **kwargs):
        queries_executed.append(args[2])
    
    response = await client.get("/api/admin/audit-logs?limit=50", headers={"Authorization": f"Bearer {admin_token}"})
    
    # Should be 1-2 queries (1 for logs+emails, 1 for count if exists)
    relevant = [q for q in queries_executed if "audit_log" in q.lower()]
    assert len(relevant) <= 2, f"N+1 detected: {len(relevant)} queries"
```

### Time Estimate: 1 hour

---

## A1.7 — Add Missing Indexes

### What
เพิ่ม indexes บน high-query columns

### Indexes to add

```sql
CREATE INDEX IF NOT EXISTS idx_files_user_id ON files(user_id);
CREATE INDEX IF NOT EXISTS idx_files_user_status ON files(user_id, processing_status);
CREATE INDEX IF NOT EXISTS idx_clusters_user_id ON clusters(user_id);
CREATE INDEX IF NOT EXISTS idx_context_packs_user_id ON context_packs(user_id);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_user_type ON graph_nodes(user_id, object_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_created ON audit_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_mcp_usage_logs_user_created ON mcp_usage_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_file_cluster_map_file ON file_cluster_map(file_id);
CREATE INDEX IF NOT EXISTS idx_file_cluster_map_cluster ON file_cluster_map(cluster_id);
CREATE INDEX IF NOT EXISTS idx_file_summaries_file ON file_summaries(file_id);
```

### Test

```python
async def test_indexes_present(db_session):
    result = await db_session.execute(text("SELECT name FROM sqlite_master WHERE type='index'"))
    indexes = {row[0] for row in result.fetchall()}
    
    required = {"idx_files_user_id", "idx_clusters_user_id", "idx_audit_logs_user_created", ...}
    missing = required - indexes
    assert not missing, f"Missing indexes: {missing}"

async def test_files_query_uses_index(db_session, user):
    plan = (await db_session.execute(text(
        f"EXPLAIN QUERY PLAN SELECT * FROM files WHERE user_id='{user.id}' LIMIT 50"
    ))).fetchall()
    plan_text = " ".join(str(row) for row in plan)
    assert "idx_files_user_id" in plan_text or "USING INDEX" in plan_text
```

### Benchmark

```python
# Before adding indexes
# Seed 50K files across 100 users
# SELECT * FROM files WHERE user_id=? LIMIT 50 → measure time

# After
# Same query → measure time
# Assert: at least 5x faster
```

### Time Estimate: 1 hour

---

## A1.8 — FK ON DELETE CASCADE

### What
เพิ่ม `ondelete="CASCADE"` ทุก FK (~30 columns)
SQLite limitation: ALTER FK ไม่ได้ตรงๆ → ต้อง table rebuild

### How

```python
# backend/database.py — model definitions
class File(Base):
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

class Cluster(Base):
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

# ... ทุก FK
```

**Migration script** (เพราะ SQLite ALTER FK ไม่ได้):

```python
# backend/migrations/0002_fk_cascade.py
async def upgrade(conn):
    """Rebuild tables with proper FK CASCADE."""
    # สำหรับแต่ละ table ที่มี FK:
    # 1. CREATE TABLE files_new (...) ON DELETE CASCADE
    # 2. INSERT INTO files_new SELECT * FROM files
    # 3. DROP TABLE files
    # 4. ALTER TABLE files_new RENAME TO files
    # 5. Recreate indexes
    
    # Use SQLAlchemy reflection
    await conn.execute(text("PRAGMA foreign_keys=OFF"))  # Disable during rebuild
    
    tables_to_rebuild = ["files", "clusters", "context_packs", "graph_nodes", ...]
    for table in tables_to_rebuild:
        # ... rebuild logic
        pass
    
    await conn.execute(text("PRAGMA foreign_keys=ON"))
```

### Test

```python
async def test_user_delete_cascades(db_session):
    user = User(email="t@x.com", ...)
    db_session.add(user)
    await db_session.commit()
    
    file = File(user_id=user.id, ...)
    cluster = Cluster(user_id=user.id, ...)
    pack = ContextPack(user_id=user.id, ...)
    db_session.add_all([file, cluster, pack])
    await db_session.commit()
    
    await db_session.delete(user)
    await db_session.commit()
    
    # ทุก child rows ต้องหาย
    assert (await db_session.execute(select(File).where(File.id == file.id))).scalar_one_or_none() is None
    assert (await db_session.execute(select(Cluster).where(Cluster.id == cluster.id))).scalar_one_or_none() is None
    assert (await db_session.execute(select(ContextPack).where(ContextPack.id == pack.id))).scalar_one_or_none() is None
```

### Rollback
Pre-migration DB backup → restore

### Time Estimate: 4-6 hours (table rebuild ระมัดระวัง)

---

## A1.9 — DB Ping ใน `/health`

### What
`/health` ปัจจุบันแค่คืน `{"ok":true}` ไม่เช็ค DB
เพิ่ม lightweight `SELECT 1` พร้อม short timeout

### How

```python
# backend/main.py:1371-1379
@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    try:
        await asyncio.wait_for(
            db.execute(text("SELECT 1")),
            timeout=2.0,
        )
        return {"ok": True, "version": APP_VERSION}
    except (asyncio.TimeoutError, Exception) as e:
        logger.error(f"Health check DB ping failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"ok": False, "version": APP_VERSION, "error": "db_unreachable"},
        )
```

### Test

```python
async def test_health_ok(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True

async def test_health_503_when_db_down(client, monkeypatch):
    async def fake_execute(*a, **kw):
        await asyncio.sleep(5)  # > 2s timeout
    monkeypatch.setattr("...", fake_execute)
    
    r = await client.get("/health")
    assert r.status_code == 503
```

### Time Estimate: 1 hour

---

## A1.10 — Input Validation Hardening

### What
- `ChatRequest.question` → `max_length=5000`
- File upload size check ไม่ trust Content-Length
- Pagination params bounds
- All other Body() / Query() without constraints

### How

```python
# backend/schemas/chat.py
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=5000)
    context_pack_ids: list[str] = Field(default_factory=list, max_length=20)
    
# backend/main.py:651-658 — upload
async def upload_files(...):
    for upload_file in files:
        contents = await upload_file.read()
        if len(contents) > max_bytes:  # Trust actual bytes, not header
            skipped.append(...)
            continue
        # ...
```

### Test

```python
async def test_chat_question_max_length(client, user_token):
    response = await client.post(
        "/api/chat",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"question": "x" * 10000},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ERR_VALIDATION"

async def test_upload_actual_size_check(client, user_token):
    # Send file ใหญ่กว่า limit จริงๆ
    large = b"x" * (max_bytes + 1000)
    response = await client.post("/api/upload", files={"files": ("big.txt", large)}, headers={...})
    body = response.json()
    assert any("big.txt" in str(s) for s in body.get("skipped", []))
```

### Time Estimate: 2 hours

---

## ✅ Sprint 1 Acceptance Gate

1. [ ] Unified error handler — sweep ทุก `str(e)` site
2. [ ] response_model ครบทุก endpoint (65+) + OpenAPI verify
3. [ ] mcp_secret หายจาก /api/me
4. [ ] MCP test endpoint คืน 401 (not 200)
5. [ ] Pagination ทำงาน /api/files + /api/clusters + /api/export + delete-account
6. [ ] N+1 audit log fix — query count ≤ 2
7. [ ] All 10 indexes present + query plan ใช้ index
8. [ ] FK cascade verified
9. [ ] /health มี DB ping
10. [ ] Input validation strict
11. [ ] Deploy + smoke test pass
12. [ ] **ส่งฟ้า review** → APPROVED

---

# 🛡 Sprint 2 — Auth + Rate Limit + LLM Safety (Days 7-11)

> รายละเอียดเต็มตามรูปแบบเดียวกัน — ขอย่อให้กระชับ

## A2.1 — Login Throttle → DB Persist
- Table `login_attempts` (email/ip, attempts, locked_until, last_attempt)
- ทำ atomic increment, lock 15 นาทีหลัง 5 fail
- **Test:** restart service → block ยังมีผล

## A2.2 — Password Reset Rate Limit
- 5/hour/email + 10/hour/IP
- **Test:** spam 6 = 429

## A2.3 — MCP Rate Limit + Auto-Rotate
- 10 wrong secrets/hour/IP → 429 + lock 1 hour
- Audit log + email alert ถ้า > 100 attempts ใน 1 hour (signal of enumeration)
- **Test:** brute force → block

## A2.4 — MCP Permissions Persist
- Table `mcp_permissions` (user_id, tool_name, enabled, updated_by, updated_at)
- เลิก in-memory dict
- **Test:** disable tool → restart → ยัง disabled

## A2.5 — LLM JSON Schema Validation
- Add Pydantic schema validation ใน `call_llm_json`
- Optional param `output_schema: type[BaseModel]`
- Validation fail → retry once → fallback ค่า default + log
- **Test:** inject `"score":"very high"` → reject + log

## A2.6 — Per-User Token Budget
- Table `user_token_usage` (user_id, month, tokens_used, cost_cents)
- Check ก่อนเรียก LLM → 429 ถ้าเกิน budget
- **Test:** user เกิน quota → clear 429 message

## A2.7 — LlamaParse Budget Guard
- Check `extraction_metadata.cost_cents_30d_total` ก่อนเรียก
- 503 ถ้าเกิน `LLAMAPARSE_BUDGET_CENTS`
- **Test:** mock spend → block

### Sprint 2 Acceptance Gate
- ทุก rate limit + budget + LLM validation ผ่าน test
- ส่งฟ้า review

---

# 🧪 Sprint 3 — Tests + Refactor + Cleanup (Days 12-16)

## A3.1 — Auth Integration Tests (≥15 tests)
- Register → email verify → login → token refresh → password reset → logout
- File: `backend/_test_auth.py`

## A3.2 — Endpoint Integration Tests (≥20 tests)
- /api/files CRUD + /api/clusters + /api/organize-new + permission isolation
- File: `backend/_test_endpoints.py`

## A3.3 — DB Tests
- Migration safety + concurrent write + WAL behavior
- File: `backend/_test_database.py`

## A3.4 — Cleanup
- ลบ `OPENROUTER_API_KEY` + `OPENROUTER_BASE_URL` constants
- `grep -r OPENROUTER backend/` = 0

## A3.5 — Refactor `init_db()` 634 LOC
- แยกเป็น `backend/migrations/0001_initial.py`, `0002_*.py`, ...
- แต่ละไฟล์ ≤100 LOC
- Migration framework: ตาม version + idempotent

## A3.6 — API Versioning `/api/v1/`
- New `/api/v1/*` routes (alias of current)
- Legacy `/api/*` → 308 redirect + Deprecation header
- **Test:** old client ยังทำงาน + new client เรียก /v1/ ได้

### Sprint 3 Acceptance Gate
- Coverage ≥ 25% (จาก 0.6%)
- ทุก test pass บน CI
- ส่งฟ้า FINAL review

---

# 🧪 Test Infrastructure

## Where Tests Live
```
backend/_test_auth.py
backend/_test_endpoints.py
backend/_test_database.py
backend/_test_config.py
backend/_test_llm.py
backend/_test_schemas.py  (validation tests)
```

## How to Run

```bash
# All A's tests
pytest backend/_test_auth.py backend/_test_endpoints.py backend/_test_database.py backend/_test_config.py backend/_test_llm.py -v

# With coverage
pytest backend/_test_*.py --cov=backend/auth --cov=backend/admin --cov=backend/database --cov=backend/main --cov-report=term-missing

# CI (B จะตั้งใน Sprint 3)
pytest -x --tb=short --maxfail=5
```

## Fixtures (สร้างที่ `conftest.py`)

```python
# backend/conftest.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

@pytest.fixture
async def db_engine(tmp_path):
    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    engine = create_async_engine(db_url)
    # init schema
    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session(db_engine):
    async with AsyncSession(db_engine) as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client(db_engine):
    from backend.main import app
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def user_token(client, db_session):
    # register + login → return JWT
    ...
```

---

# 🤝 Coordination with เขียว-B

## Files ที่ A ต้องแจ้ง B เปลี่ยน

| When | What | How |
|------|------|-----|
| Sprint 1 A1.5 ตอนทำ pagination | Frontend ต้อง handle `next_cursor` + paginated list | เขียน `for-เขียว-B.md`: "A1.5 Pagination spec — frontend ต้อง...” |
| Sprint 1 A1.1 unified error | Frontend ต้อง parse `{"error":{"code","message"}}` | เขียน inbox: "API contract change — error shape" |
| Sprint 1 A1.3 mcp_secret ลบ | Frontend ต้องเปลี่ยน flow ขอ MCP credentials | เขียน inbox + provide new endpoint spec |
| Sprint 3 A3.6 API v1 | Frontend ต้องเรียก /api/v1/* | เขียน inbox + grace period |

## B request A เปลี่ยนไฟล์ของ A

| Source | Reason | A's action |
|--------|--------|-----------|
| B0.4 | embedding default ต้องเปลี่ยน | A merge ตอน Sprint 0 |
| B1.9 | `_login_fail_history` cap (อยู่ main.py) | A merge ตอน Sprint 2 (รวมกับ A2.1) |
| B2.7 | LLM_MODEL_PRO → gemini-2.5-pro | A merge ตอน Sprint 2 |
| B2.11 | File magic bytes (ต้อง integrate กับ main.py upload handler) | A merge ตอน Sprint 1 |

**Inbox protocol:**
- เขียนใน `.agent-memory/communication/inbox/for-เขียว-A.md` (B → A)
- A ตอบใน `.agent-memory/communication/inbox/for-เขียว-B.md` (A → B)
- ใช้ MSG ID + Reply chain เหมือน pattern ของฟ้า

---

# ⚠️ Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| A0.1 git filter-repo เสีย local repo | LOW | HIGH | Backup `.git` ก่อนทำ + test บน clone ก่อน |
| A0.3 plaintext drop ทำลายข้อมูล admin ต้องการ | LOW | MED | Phase 1+2 deploy 24h ก่อน Phase 3 + verify admin ไม่มีดราม่า |
| A0.4 JWT enforce ทำให้ Fly deploy พัง | MED | HIGH | Stage secret ก่อน deploy code |
| A1.2 65+ endpoints response_model = scope creep | HIGH | MED | Phased rollout — 10-15 endpoints/day, prioritize public-facing |
| A1.5 pagination break frontend | HIGH | MED | Coordinate กับ B แต่ต้น sprint + grace period (return both old + new shape) |
| A1.7 indexes สร้างนานบน DB ใหญ่ | MED | LOW | สร้างตอน maintenance window + IF NOT EXISTS |
| A1.8 FK cascade table rebuild = downtime | MED | HIGH | Test บน staging clone ก่อน + backup |
| A2.5 LLM validation reject valid output (false positive) | MED | MED | Permissive schema + log unmatched + iterate |
| A3.5 init_db refactor break existing migration | MED | HIGH | Keep old init_db เป็น compatibility layer 1 sprint |
| A3.6 API v1 break old client | LOW | MED | Legacy /api/* redirect 30 days + deprecation header |

---

# 🔵 ฟ้า Review Cadence

| Sprint End | ฟ้า ทำอะไร |
|-----------|-----------|
| **Sprint 0** | Security smoke: rotate verified + plaintext gone + JWT enforce + FK on |
| **Sprint 1** | API contract: error shape + response_model + pagination + indexes + cascade + /health DB ping |
| **Sprint 2** | Rate limits + LLM validation + token budget + MCP permissions persist |
| **Sprint 3** | Test coverage ≥25% + API v1 + init_db refactor + cleanup |
| **FINAL** | UI test ครบ Phase 1-7 ตาม [fix-plan-fa-final-test.md] |

---

# ✅ Definition of Done (per milestone)

1. ✅ Code committed + push to `fix/A-sprint-X`
2. ✅ Unit/integration tests pass locally
3. ✅ CI green (เมื่อ B set ตอน Sprint 3)
4. ✅ Manual smoke test ผ่าน
5. ✅ Memory file updated (`.agent-memory/current/pipeline-state.md`)
6. ✅ Inbox update — ส่งฟ้า ตอน sprint end
7. ✅ Merge หลัง ฟ้า APPROVED

---

# 📞 Communication Touchpoints

- **Daily:** Self-status update ใน `.agent-memory/current/last-session.md`
- **Inbox check:** ทุกเช้า + ก่อน start milestone (B อาจมี request)
- **Sprint end:** ส่ง MSG ให้ฟ้า review ใน `for-ฟ้า.md`
- **Blocker:** ถ้าติด > 2 ชม. ใน 1 milestone → flag ใน inbox + ขอความช่วยเหลือ user/B

---

# 📊 Success Metrics

| Metric | Baseline | Target (End Sprint 3) |
|--------|----------|----------------------|
| P0 findings closed (A scope) | 0 / 12 | 12 / 12 |
| Test coverage (A files) | ~5% | ≥25% |
| `str(e)` in main.py | 14 | 0 |
| Endpoints with response_model | 0 | 65+ |
| Indexes on user_id columns | 0 | 5+ |
| FKs without CASCADE | ~30 | 0 |
| sys.exit on missing env | 1 (ADMIN_PASSWORD) | 0 (replaced by warn+503) |
| `OPENROUTER_*` references | 4 | 0 |

---

**End of plan — เขียว-A อ่านครบแล้วเริ่ม Sprint 0 ได้เลย**
