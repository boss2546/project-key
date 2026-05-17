# 🔥 Fix Plan — Urgent Hotfix Only

> **Scope:** 6 รายการเร่งด่วน · ~1-2 วัน
> **Created:** 2026-05-18 (v4 = scope reduced per user · เน้นแค่ critical)
> **Owner:** เขียวคนเดียว (me) · **Reviewer:** ฟ้า
> **Backlog:** 60+ items อื่น ๆ ดู [`issues-backlog.md`](./issues-backlog.md)

---

## 🎯 Mission

ปิด 6 รูร้ายแรงสุด ที่ถ้าทิ้งไว้ = อันตรายตอนนี้
อย่างอื่นพักไว้ก่อน · ทำตอนมีเวลา

---

## 📋 6 รายการ + ลำดับ

### 1. 🛡 Chat XSS Fix (30 min · ทำเลย)
**ปัญหา:** AI response มี HTML → frontend รัน HTML นั้นเลย → hacker inject `<script>` ผ่าน prompt ได้
**File:** `legacy-frontend/app.js:5118`
**Fix:** ลบ `isHtml` flag · ใช้ `textContent` หรือ escape เสมอ
**Test:** inject `<script>alert(1)</script>` ใน LLM response → escape (ไม่ run)
**Risk:** 🟢 LOW · 1 ไฟล์ frontend
**Deploy:** ทันทีหลังเสร็จ

### 2. 🐳 Dockerfile Non-root + .dockerignore (45 min)
**ปัญหา:** Container รัน root · image มี `.env`/cache
**Files:** `Dockerfile`, `.dockerignore`
**Fix:**
- Add `USER app` + `HEALTHCHECK`
- `.dockerignore` เพิ่ม `__pycache__`, `.env*`, `.venv`, `*.db`
**Test:** `docker run` → user != root · `docker exec ls /app/.env` → not found
**Risk:** 🟢 LOW · ไม่กระทบ runtime
**Deploy:** combine กับ #1

### 3. 🔐 JWT + ADMIN_PASSWORD Bulletproof (1h)
**ปัญหา:**
- JWT ใช้ไฟล์ fallback → scale 2+ machines = auth พัง
- ADMIN_PASSWORD หาย = `sys.exit(1)` ทั้ง app
**File:** `backend/config.py:144-196`
**Fix:**
- JWT: ถ้ารันบน Fly (`/app/data` exists) + `JWT_SECRET_KEY` ไม่ตั้ง → fail-hard
- ADMIN_PASSWORD: ว่าง = warn (ไม่ exit) · admin endpoints คืน 503
**Pre-deploy:** `flyctl secrets set --stage JWT_SECRET_KEY=$(openssl rand -base64 64)` ก่อน deploy
**Test:**
- Mock `/app/data` + delete env → import ต้อง raise SystemExit
- Delete ADMIN_PASSWORD → import ผ่าน · admin endpoint → 503
**Risk:** 🟡 MED · ถ้า Fly secret ยังไม่ตั้ง = deploy ขึ้นไม่ได้ (ดี กันลืม)
**Deploy:** combine กับ #1 + #2 + ก่อน #5 (JWT secret stage ก่อน)

### 4. 🔑 Rotate Secrets + Clean .env from Git (2-3h)
**ปัญหา:** Secret อยู่ใน `.env` ที่ถูก commit เข้า git history — public ใน GitHub
**Files:** `.env`, git history, Fly secrets, external consoles
**Sequence:**
1. **User ไปแต่ละ console revoke + create new** (อยู่นอก scope code):
   - openrouter.ai/keys (OPENROUTER_API_KEY)
   - dashboard.stripe.com/apikeys (STRIPE_SECRET_KEY)
   - console.cloud.google.com (GOOGLE_OAUTH_CLIENT_SECRET, GOOGLE_PICKER_API_KEY, GOOGLE_API_KEY)
   - cloud.llamaindex.ai (LLAMA_CLOUD_API_KEY)
2. **User ส่งให้ผม** หรือตั้ง Fly secret ด้วยตัวเอง: `flyctl secrets set KEY=value -a personaldatabank`
3. **ผม clean git history:**
   ```bash
   cp -r .git ../PDB-git-backup
   git filter-repo --invert-paths --path .env --force
   git push --force --all origin
   ```
4. **Smoke test** ทุก integration: login + LLM + Drive OAuth + LINE webhook
**Test:**
- `/health` 200 หลัง rotate
- Login + chat ทำงาน · Drive OAuth init ทำงาน
- `git log --all -- .env` ว่างเปล่า
**Risk:** 🔴 HIGH · `git filter-repo` destructive · external service downtime ถ้า rotate ผิด
**Mitigation:** Backup `.git` ก่อน · test rotate ทีละ key + smoke test แต่ละ
**Deploy:** ไม่ต้อง code deploy (Fly secret update auto-restarts)

### 5. 🔓 Drop `plaintext_password` Column — Phase 1+2 (2h, Phase 3 รอ 24h)
**ปัญหา:** เก็บ password เป็น plaintext ใน DB → DB leak = หายนะ · ผิด PDPA/GDPR
**Files:** `backend/auth.py:128`, `backend/admin.py:507`, `backend/main.py:2281`, `backend/config.py:198`, `backend/database.py:58`
**Phase 1 — stop writes (deploy ทันที):**
- ลบ `plaintext_password=password if _ALLOW_VIEW_PWD else None` จาก register
**Phase 2 — remove endpoint (deploy ทันที):**
- ลบ admin view-password endpoint + admin_view_password helper
- ลบ `ALLOW_ADMIN_VIEW_PASSWORD` constant
**Phase 3 — DROP COLUMN (รอ 24h หลัง Phase 1+2 deploy):**
- backup DB ก่อน
- `ALTER TABLE users DROP COLUMN plaintext_password` (SQLite 3.35+)
**Test:**
- Phase 1+2: register new user → DB row ไม่มี plaintext · `/api/admin/users/{id}/password` → 404
- Phase 3: `PRAGMA table_info(users)` → ไม่มี column
**Risk:** 🟡 MED · DROP COLUMN ทำลายข้อมูลถาวร · pre-migration backup ป้องกัน
**Deploy:** Phase 1+2 = วันที่ 1 · Phase 3 = วันที่ 2

### 6. 🔄 Backup Gemini Key (30 min)
**ปัญหา:** Primary key เดียว · key ดับ = AI ทั้งระบบใช้ไม่ได้
**File:** Fly secrets (no code change · failover logic มีอยู่แล้วใน `llm.py`)
**Sequence:**
1. User สร้าง Gemini API key อีก 1 ตัว (อย่าซ้ำกับ primary)
2. User ส่งให้ผม **หรือ** ตั้งเอง:
   ```bash
   flyctl secrets set GEMINI_API_KEY_BACKUP=<new-key> -a personaldatabank
   ```
3. Smoke test failover (จำลอง 429 บน primary → backup รับ)
**Test:**
- `flyctl secrets list` มี `GEMINI_API_KEY_BACKUP`
- Mock primary 429 → log แสดง "failing over to backup key" → response ผ่าน
**Risk:** 🟢 LOW · failover code มีอยู่แล้ว · 1 secret added
**Deploy:** ไม่ต้อง code deploy

---

## 📅 Execution Order

| Day | Item | Type | Time |
|----:|------|------|-----:|
| 1 | #1 Chat XSS | code | 30m |
| 1 | #2 Dockerfile | code | 45m |
| 1 | #3 JWT/ADMIN | code + Fly secret stage | 1h |
| 1 | #4 Rotate secrets | user + code (git filter-repo) | 2-3h |
| 1 | #5 Plaintext Phase 1+2 | code | 2h |
| 1 | #6 Backup key | user + Fly secret | 30m |
| 1 | **Deploy combined** | flyctl deploy | 5m |
| 1 | Smoke test all 6 | manual | 30m |
| 2 | **Wait 24h** | — | — |
| 2 | #5 Plaintext Phase 3 (DROP COLUMN) | code + migration | 30m |
| 2 | **Deploy Phase 3** | flyctl deploy | 5m |

**รวม:** Day 1 ~7-8 ชม. (รวม user + ผม) · Day 2 ~1 ชม. · Total ~9 ชม. across 2 days

---

## 🚀 Deploy Procedure

1. **Pre-deploy:** `flyctl postgres backup` (DB backup) · tag `v10.0.30-hotfix`
2. **Stage Fly secrets:** ทุก secret (rotate keys, backup key, JWT) ก่อน deploy code
3. **Deploy code:** `flyctl deploy --remote-only`
4. **Watch logs:** `flyctl logs -a personaldatabank --tail` (5 min)
5. **Smoke test:**
   - `/health` 200 + version `10.0.30-hotfix`
   - Login + 1 chat + 1 upload
   - Admin endpoint (if no ADMIN_PASSWORD = 503, if set = 200)
6. **Cool-down:** 30 min monitor logs
7. **Rollback if regress:** `flyctl releases rollback`

---

## ✅ Acceptance Gate

ผ่านเมื่อ:
- [ ] **#1** Chat XSS — `<script>` injection ใน LLM response = escape (ทดสอบจริง)
- [ ] **#2** Container `whoami` != root · image ไม่มี `.env*`
- [ ] **#3** Fly without `JWT_SECRET_KEY` env = container refuse start · ADMIN missing = warn + admin 503
- [ ] **#4** Smoke test 4 integrations (LLM, Drive, LINE, Stripe) pass · `git log -- .env` empty
- [ ] **#5** Phase 1+2: register no plaintext + admin endpoint 404 · Phase 3 (วันที่ 2): column gone
- [ ] **#6** `flyctl secrets list | grep BACKUP` มี · failover log มี
- [ ] Combined deploy `v10.0.30-hotfix` + smoke 30 min cool-down + no rollback
- [ ] ส่ง ฟ้า review ผ่าน `for-ฟ้า.md`

---

## 📞 What User Needs to Help

| Item | User Action | Time |
|------|-------------|-----:|
| #4 | Revoke + create 6 keys ใน 4 consoles | ~1h |
| #6 | สร้าง Gemini key ตัวที่ 2 + ส่ง/ตั้งเอง | ~10min |
| #3 (pre) | Run `flyctl secrets set --stage JWT_SECRET_KEY=$(openssl rand -base64 64)` ก่อน deploy | ~5min |

ที่เหลือผมทำเองได้

---

## 🟡 อื่น ๆ พักไว้

ที่เหลือ 60+ items (Thai tokenizer, pagination, tests, CI/CD, memory leaks, rate limits, etc.) → ดู [`issues-backlog.md`](./issues-backlog.md)

ทำตอนระบบเสถียร · มี user feedback · มีเวลา

---

**End of urgent plan — 6 items, 2 days**
