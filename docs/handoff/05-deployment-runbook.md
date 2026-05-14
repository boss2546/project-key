# 05 — Deployment Runbook

> **Purpose:** Step-by-step procedures สำหรับ deploy PDB จาก zero → production
> **Coverage:** Local dev → Fly.io prod → Secrets → Volume → Logs → Incident response
> **Target:** Solo developer หรือ small team

---

## ตารางสรุป

| Phase | Time | Purpose |
|---|---|---|
| 1. Local Dev Setup | 30 min | รัน app บนเครื่องตัวเอง |
| 2. Fly.io Account + CLI | 15 min | เตรียม cloud account |
| 3. Generate Secrets | 10 min | สร้าง JWT key + Fernet key + admin password |
| 4. External API Keys | 1-2 hr | ดู Doc 06 |
| 5. First Deploy | 30 min | flyctl launch + secrets + volume |
| 6. Verify Deployment | 15 min | Smoke test all endpoints |
| 7. Operations | ongoing | Logs, metrics, incident playbook |

---

## Phase 1 — Local Dev Setup

### 1.1 System Requirements

| Component | Version | Notes |
|---|---|---|
| OS | Windows 11 / macOS 12+ / Ubuntu 22+ | Tesseract + poppler ต้องลงเอง |
| Python | **3.11** (slim) | ไม่ต้องเป็น 3.12 (untested) |
| Node | 18+ | สำหรับ Playwright tests เท่านั้น |
| Git | 2.30+ | |
| Disk | 5 GB free | venv + Docling ~2GB |

### 1.2 Clone & Setup

```bash
# Clone
git clone <your-repo> pdb
cd pdb

# Python venv
python3.11 -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate

# Install deps (use requirements.txt = full dev, includes Docling + ChromaDB)
pip install -r requirements.txt

# System packages — REQUIRED for OCR
# Ubuntu:
sudo apt-get install -y tesseract-ocr tesseract-ocr-tha tesseract-ocr-eng poppler-utils

# macOS:
brew install tesseract tesseract-lang poppler

# Windows:
# 1. Install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki
# 2. Install Thai language data (.traineddata)
# 3. Add tesseract.exe to PATH
# 4. Install poppler: https://github.com/oschwartz10612/poppler-windows
```

### 1.3 Environment Variables (.env)

สร้างไฟล์ `.env` ใน project root:

```bash
# ─── Core ───
APP_VERSION=9.4.8
APP_BASE_URL=http://localhost:8000
DATA_DIR=./data
DATABASE_URL=sqlite+aiosqlite:///./data/projectkey.db

# ─── Auth ───
JWT_SECRET_KEY=<generate via: openssl rand -base64 64>
JWT_EXPIRE_MINUTES=1440
ADMIN_PASSWORD=<any-secure-password>
ADMIN_EMAILS=your@email.com

# ─── LLM ───
OPENROUTER_API_KEY=sk-or-v1-...
GOOGLE_API_KEY=AIza...
GEMINI_FILE_MODEL=gemini-2.5-flash

# ─── Google OAuth + Drive BYOS ───
GOOGLE_OAUTH_CLIENT_ID=<from Google Cloud Console>.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-...
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/api/drive/oauth/callback
GOOGLE_OAUTH_MODE=testing
DRIVE_TOKEN_ENCRYPTION_KEY=<generate via Fernet.generate_key()>

# ─── Stripe ───
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_STARTER=price_...

# ─── Email ───
RESEND_API_KEY=re_...

# ─── LINE Bot ───
LINE_CHANNEL_SECRET=...
LINE_CHANNEL_ACCESS_TOKEN=...

# ─── Worker tuning ───
UPLOAD_WORKER_POLL_SEC=2.0
UPLOAD_MAX_RETRY=3
```

### 1.4 Generate Secrets

```bash
# JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(64))"

# DRIVE_TOKEN_ENCRYPTION_KEY (Fernet)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# ADMIN_PASSWORD — any strong password
```

### 1.5 Init Database

```bash
# Database creates itself on first FastAPI startup
# Schema migration is idempotent (PRAGMA table_info checks)
mkdir -p data/uploads data/summaries data/context_packs data/backups
```

### 1.6 Run

```bash
# Activate venv if not already
source .venv/bin/activate

# Run
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Browser
open http://localhost:8000
```

### 1.7 Verify Local Setup

| Check | Expected |
|---|---|
| `GET /` | landing.html (200) |
| `GET /app` | app.html (200, requires login) |
| `GET /docs` | Swagger UI (FastAPI auto) |
| `GET /api/healthz/queue` | `{queued: 0, processing: 0, worker_alive: true}` |
| Register → login | Should work + JWT issued |
| Upload TXT file | Worker picks up in ≤ 2s, status=uploaded after extract |

---

## Phase 2 — Fly.io Account + CLI

### 2.1 Install flyctl

```bash
# macOS / Linux
curl -L https://fly.io/install.sh | sh

# Windows
iwr https://fly.io/install.ps1 -useb | iex
```

### 2.2 Sign up + Auth

```bash
flyctl auth signup       # หรือ flyctl auth login
flyctl auth whoami       # Verify
```

### 2.3 Add Payment Method

- Visit https://fly.io/dashboard → Billing
- Add credit card (Hobby plan ~$2-5/mo for 2 GB machine)

---

## Phase 3 — Generate Production Secrets

ทำตาม §1.4 ใน Local Setup แต่:
- **JWT_SECRET_KEY**: คนละ key กับ dev — ห้ามใช้ซ้ำ
- **ADMIN_PASSWORD**: คนละ password
- **DRIVE_TOKEN_ENCRYPTION_KEY**: คนละ key — ถ้าเปลี่ยน existing user's Drive tokens จะ decrypt ไม่ได้

**Backup secrets** ที่ปลอดภัย (1Password, Bitwarden, secure note) — ถ้าหาย:
- JWT key หาย = users ทุกคน logout
- Fernet key หาย = ทุก Drive connection ใช้ไม่ได้

---

## Phase 4 — External API Keys

ดู [06-external-api-setup.md](06-external-api-setup.md) — full step-by-step สำหรับ Gemini / OpenRouter / Stripe / Google OAuth / Resend / LINE

---

## Phase 5 — First Deploy to Fly.io

### 5.1 Launch App (First Time Only)

```bash
cd pdb
flyctl launch
```

Prompts:
- App name: `your-pdb-name` (must be globally unique)
- Region: `sin` (Singapore) หรือ region ใกล้ user
- Postgres: **No**
- Redis: **No**
- Deploy now: **No** (เราจะ set secrets ก่อน)

จะได้ไฟล์ `fly.toml` (เช็คให้ตรงกับต้นแบบ):

```toml
app = "your-pdb-name"
primary_region = "sin"

[build]

[env]
  PORT = "8000"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = "stop"
  auto_start_machines = true
  min_machines_running = 1
  processes = ["app"]

[[vm]]
  memory = "2048mb"
  cpu_kind = "shared"
  cpus = 2

[mounts]
  source = "pdb_data"
  destination = "/app/data"
```

### 5.2 Create Volume

```bash
flyctl volumes create pdb_data --region sin --size 10
# 10 GB = พอสำหรับ ~1000 free tier users
```

### 5.3 Set Secrets

```bash
# Core
flyctl secrets set \
  JWT_SECRET_KEY="<production-key>" \
  ADMIN_PASSWORD="<production-password>" \
  ADMIN_EMAILS="founder@yoursite.com" \
  APP_BASE_URL="https://your-pdb-name.fly.dev" \
  APP_VERSION="9.4.8"

# LLM
flyctl secrets set \
  OPENROUTER_API_KEY="sk-or-v1-..." \
  GOOGLE_API_KEY="AIza..." \
  GEMINI_FILE_MODEL="gemini-2.5-flash"

# Google OAuth + Drive (after setup per Doc 06)
flyctl secrets set \
  GOOGLE_OAUTH_CLIENT_ID="...apps.googleusercontent.com" \
  GOOGLE_OAUTH_CLIENT_SECRET="GOCSPX-..." \
  GOOGLE_OAUTH_REDIRECT_URI="https://your-pdb-name.fly.dev/api/drive/oauth/callback" \
  GOOGLE_OAUTH_MODE="testing" \
  DRIVE_TOKEN_ENCRYPTION_KEY="<production-fernet-key>"

# Stripe
flyctl secrets set \
  STRIPE_SECRET_KEY="sk_live_..." \
  STRIPE_WEBHOOK_SECRET="whsec_..." \
  STRIPE_PRICE_ID_STARTER="price_..."

# Email + LINE
flyctl secrets set \
  RESEND_API_KEY="re_..." \
  LINE_CHANNEL_SECRET="..." \
  LINE_CHANNEL_ACCESS_TOKEN="..."
```

### 5.4 First Deploy

```bash
flyctl deploy
# จะ build Docker image → push → boot machine
# ใช้เวลา ~3-5 นาที
```

### 5.5 Verify

```bash
# Check status
flyctl status

# Watch logs
flyctl logs

# Open
flyctl open
# → opens https://your-pdb-name.fly.dev
```

---

## Phase 6 — Post-Deploy Verification

### 6.1 Smoke Checklist

| Test | Expected | Command |
|---|---|---|
| Landing page loads | landing.html 200 | `curl https://your-pdb-name.fly.dev/` |
| App page loads | app.html 200 | `curl https://your-pdb-name.fly.dev/app` |
| Health endpoint | `worker_alive: true` | `curl /api/healthz/queue` |
| Register new user | 201 + JWT | via UI |
| Login | JWT returned | via UI |
| Upload small TXT | status=uploaded ใน 5s | via UI |
| Upload PDF | OCR runs, status=uploaded | via UI |
| Organize | clusters created | via UI |
| Chat | answer with sources | via UI |
| MCP setup | URL + tools listed | via /app#mcp-setup |

### 6.2 Run Smoke Scripts (Optional)

```bash
# จาก scripts/ ใน repo
python scripts/prod_upload_smoke.py --url https://your-pdb-name.fly.dev
```

---

## Phase 7 — Operations & Incident Response

### 7.1 View Logs

```bash
# Live tail
flyctl logs

# Specific machine
flyctl logs --instance <machine-id>

# Filter by region (multi-region setup)
flyctl logs --region sin
```

### 7.2 SSH into Machine

```bash
flyctl ssh console
# → Bash shell inside container
# → /app/data/ has volume contents
```

### 7.3 Database Backup

```bash
# SSH in
flyctl ssh console

# Inside container
sqlite3 /app/data/projectkey.db ".backup /app/data/backups/manual_$(date +%Y%m%d).db"

# Download backup to local
flyctl ssh sftp shell
# Then in sftp:
get /app/data/backups/manual_20260513.db
```

**Automation (cron-like via Fly.io Schedule):**

```toml
# Add to fly.toml
[[machines]]
  schedule = "daily"
  command = "sqlite3 /app/data/projectkey.db .backup /app/data/backups/daily_$(date +%Y%m%d).db"
```

### 7.4 Common Incidents

#### A. Worker Stuck / Queue Backed Up

**Symptoms:**
- `GET /api/healthz/queue` shows `worker_alive: false` หรือ `queued > 20`
- Users see "ระบบประมวลผลหยุด" banner

**Diagnose:**
```bash
flyctl logs | grep -i "worker\|extracting\|heartbeat"
```

**Fix:**
```bash
# Restart worker
flyctl machine restart <machine-id>

# Or full redeploy
flyctl deploy --strategy immediate
```

The recovery sweep on startup will reset all `extracting` → `queued` (v9.4.5).

---

#### B. Gemini API 503 / Quota Exceeded

**Symptoms:**
- Upload of audio/video/image fails with `GEMINI_UNAVAILABLE` or `QUOTA_EXCEEDED`
- Logs show `google.api_core.exceptions.ServiceUnavailable`

**Diagnose:**
```bash
# Check current quota
# Visit https://aistudio.google.com/app/apikey
# Or:
curl https://generativelanguage.googleapis.com/v1beta/models?key=$GOOGLE_API_KEY
```

**Fix (short-term):**
- Wait 1 minute (rate limit window)
- Tell users to retry — failed uploads have retry button

**Fix (long-term):**
- Upgrade to paid Gemini tier (15 → 360 RPM)
- Set `flyctl secrets set GOOGLE_API_KEY=<new-billed-key>`

---

#### C. Drive Sync RefreshError (invalid_grant)

**Symptoms:**
- User's Drive panel shows "เชื่อมต่อหมดอายุ" banner
- `last_sync_status='error'`, `last_sync_error='INVALID_GRANT'`

**Cause:** `GOOGLE_OAUTH_MODE=testing` → tokens expire after 7 days

**User self-fix:**
- Click "Reconnect" banner → re-do OAuth flow

**Long-term fix:**
- Submit Google OAuth verification (founder action — see SDD §17.1 STORAGE-007)
- After approval: `flyctl secrets set GOOGLE_OAUTH_MODE=production`

---

#### D. Stripe Webhook Failing

**Symptoms:**
- Users pay but subscription_status doesn't update
- `webhook_logs.status='error'`

**Diagnose:**
```bash
flyctl logs | grep -i stripe

# Check Stripe Dashboard → Webhooks → see delivery attempts
```

**Common causes:**
- Wrong `STRIPE_WEBHOOK_SECRET` → signature verify fail
- Network timeout → Stripe retries automatically (within idempotency window)

**Fix:**
```bash
# Re-fetch correct webhook secret from Stripe Dashboard
flyctl secrets set STRIPE_WEBHOOK_SECRET="whsec_..."
```

---

#### E. Disk Full

**Symptoms:**
- Upload returns 500 with `OSError [Errno 28]` (no space left)
- `flyctl status` shows volume near 100%

**Diagnose:**
```bash
flyctl ssh console
df -h /app/data
du -sh /app/data/*
```

**Quick fix:**
- Delete old backups: `rm /app/data/backups/old_*.db`
- Trim user data if BYOS available

**Long-term:**
- Extend volume: `flyctl volumes extend <vol-id> --size 20`

---

#### F. SQLite Lock / WAL File Huge

**Symptoms:**
- Slow queries
- `projectkey.db-wal` > 100 MB

**Fix:**
```bash
flyctl ssh console
sqlite3 /app/data/projectkey.db "PRAGMA wal_checkpoint(TRUNCATE);"
```

---

#### G. Machine OOM (PDF ใหญ่)

**Symptoms:**
- Logs: `OOMKilled` or process restart
- Big PDF upload (>50 pages OCR)

**Fix:**
- Reduce `ABSOLUTE_MAX_FILE_SIZE_MB` (in config.py)
- Bump machine memory: `flyctl scale memory 4096`

---

#### H. Cold Start Slow

**Cause:** `auto_stop_machines = "stop"` → first request after idle = 5-10s wake

**Acceptable trade-off** for cost saving

**If unacceptable:**
- Change to `auto_stop_machines = "suspend"` (faster wake, higher cost)
- Or `min_machines_running = 1` already set — but if = 0, this is the issue

---

### 7.5 Common flyctl Commands

```bash
# Status + machine info
flyctl status
flyctl machine list

# Logs
flyctl logs
flyctl logs --instance <id>

# Restart
flyctl machine restart <id>

# Scale
flyctl scale count 2          # 2 machines
flyctl scale memory 4096      # 4 GB RAM
flyctl scale vm shared-cpu-4x # 4 CPU shared

# Secrets
flyctl secrets list
flyctl secrets set KEY=value
flyctl secrets unset KEY

# Volume
flyctl volumes list
flyctl volumes extend <vol-id> --size 20

# Deploy
flyctl deploy                                 # default
flyctl deploy --strategy immediate            # zero-downtime override
flyctl deploy --dockerfile Dockerfile         # specify file

# Open SSH
flyctl ssh console
flyctl ssh sftp shell

# DNS / Domain
flyctl certs list
flyctl certs add yourdomain.com
```

---

## Phase 8 — Custom Domain (Optional)

### 8.1 Add Certificate

```bash
flyctl certs add yourdomain.com
# จะแสดง DNS records ที่ต้องเพิ่ม
```

### 8.2 Set DNS Records

ใน Cloudflare หรือ DNS provider ของคุณ:

| Type | Name | Value | Proxy |
|---|---|---|---|
| A | @ | <Fly.io IPv4> | Yes (Cloudflare) |
| AAAA | @ | <Fly.io IPv6> | Yes |
| CNAME | www | yourdomain.com | Yes |
| TXT | _acme-challenge.yourdomain.com | <from flyctl> | No |

### 8.3 Verify

```bash
flyctl certs check yourdomain.com
# จะแสดง issued ✓ เมื่อเสร็จ
```

### 8.4 Update APP_BASE_URL

```bash
flyctl secrets set APP_BASE_URL=https://yourdomain.com
flyctl secrets set GOOGLE_OAUTH_REDIRECT_URI=https://yourdomain.com/api/drive/oauth/callback
```

### 8.5 Update External Services

ต้องอัปเดต redirect URIs ใน:
- Google Cloud Console (OAuth credentials)
- Stripe Dashboard (webhook URL)
- LINE Developers Console (webhook URL)

---

## Phase 9 — Monitoring & Alerts

### 9.1 Built-in Health Endpoint

```bash
# Periodically check
curl https://yourdomain.com/api/healthz/queue
```

Response structure:
```json
{
  "queued": 0,
  "processing": 1,
  "worker_alive": true,
  "worker_uptime_sec": 1234,
  "success_24h": 56,
  "error_24h": 0,
  "avg_extract_sec_by_class": {"1": 1.0, "2": 13.27, "3": 74.29}
}
```

### 9.2 Alerts (External — Solo Founder Setup)

แนะนำใช้ **UptimeRobot** (free):
- Monitor: `GET /api/healthz/queue` every 5 min
- Alert: Email + Slack/Discord webhook ถ้า status ≠ 200 หรือ `worker_alive=false`

หรือ **BetterStack** (free tier):
- Logs aggregation
- Status page

### 9.3 Cost Tracking

```bash
# Fly.io billing
flyctl dashboard  # ดู usage + cost

# Stripe
# Visit Stripe Dashboard → Revenue

# Gemini
# Visit https://aistudio.google.com → API quota usage

# OpenRouter
# Visit https://openrouter.ai/credits
```

---

## Phase 10 — Rollback

### Quick Rollback

```bash
# List releases
flyctl releases

# Rollback to specific version
flyctl releases rollback <release-id>
```

### Database Rollback

```bash
# SSH in
flyctl ssh console

# Stop accepting writes (optional — usually safe)
# Restore from backup
cp /app/data/backups/daily_20260512.db /app/data/projectkey.db
cp /app/data/backups/daily_20260512.db-wal /app/data/projectkey.db-wal  # if exists

# Restart
flyctl machine restart <id>
```

---

**End — Production runbook for PDB v9.4.8**

**Estimated total deploy time from zero:** 6-8 hours (first time, including external API setup per Doc 06)
**Recurring deploys:** 5-10 minutes (`flyctl deploy`)
