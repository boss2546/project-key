# 🟢 BYOS Setup Guide — Google Drive Bring-Your-Own-Storage

> **For:** Personal Data Bank (PDB) administrators / self-hosters
> **Feature:** v7.0.0 — Google Drive BYOS Mode
> **Time:** ~30-45 minutes
> **Difficulty:** Medium (one-time setup; no coding required)

---

## 📚 What is BYOS?

By default, PDB stores user data on the **server** (managed mode):
- ไฟล์ที่ user upload → `/uploads/` folder บน Fly.io volume
- AI summaries, profile, knowledge graph → `pdb.db` SQLite

In **BYOS mode**, user data lives on **the user's own Google Drive**:
- Folder `/Personal Data Bank/` ใน Drive ของ user
- Server เก็บแค่ index + cache (rebuildable จาก Drive)
- **ลูกค้าเปิด Drive ดูเองได้** — เห็นทุกไฟล์ + summaries + profile.json
- ถ้า PDB ปิดบริการ → ลูกค้ายังมีข้อมูลครบใน Drive

**Differentiator:** "Your data stays in YOUR Drive — verify anytime"

---

## 🎯 What this guide covers

ขั้นตอน admin (พี่/เจ้าของ instance) ต้องทำเพื่อ enable BYOS feature:

1. ✅ สร้าง Google Cloud Project
2. ✅ Enable Drive API + Picker API
3. ✅ Configure OAuth Consent Screen (Testing Mode)
4. ✅ Create OAuth 2.0 Client ID
5. ✅ Create API Key สำหรับ Picker
6. ✅ หา Project Number
7. ✅ Set 5 environment variables ใน production
8. ✅ Generate refresh-token encryption key

ทำเสร็จแล้ว → BYOS endpoints จะเลิก return `503 GOOGLE_OAUTH_NOT_CONFIGURED` →
ลูกค้าใน Test users list สามารถ "Connect Drive" ได้

---

## 🚀 Step-by-Step

### Step 1 — Create Google Cloud Project (5 min)

1. Open https://console.cloud.google.com
2. ล็อกอินด้วย Google account ของ admin (ไม่จำเป็นต้องเป็น account ลูกค้า)
3. มุมบนซ้าย → dropdown "Select a project" → **NEW PROJECT**
4. Project name: `Personal Data Bank` (หรือ `PDB BYOS`)
5. **CREATE** → wait 30s
6. **เลือก project ที่เพิ่งสร้าง** จาก dropdown (สำคัญ — ทุก step ต้องอยู่ใน project ใหม่)

### Step 2 — Enable APIs (3 min)

1. เมนูซ้าย (☰) → **APIs & Services** → **Library**
2. ค้นหา `Google Drive API` → click → **ENABLE**
3. ย้อนกลับไป Library → ค้นหา `Google Picker API` → click → **ENABLE**

### Step 3 — OAuth Consent Screen (10 min)

ที่ลูกค้าจะเห็นตอนกด "Connect Drive" → "Personal Data Bank wants to access your Google Drive"

1. **APIs & Services** → **OAuth consent screen**
2. User Type: **External** → **CREATE**
3. กรอก:
   ```
   App name:               Personal Data Bank
   User support email:     <admin email>
   Developer contact:      <admin email>
   App logo:               (optional — ใส่ทีหลังได้)
   Application home page:  https://your-domain.com (optional)
   Authorized domains:     your-domain.com (optional ใน Testing Mode)
   ```
4. **SAVE AND CONTINUE**
5. **Scopes** page → **SAVE AND CONTINUE** (ไม่เพิ่มอะไร — แอป request scope ตอน OAuth flow เอง)
6. **Test users** page → **+ ADD USERS** → ใส่ email beta testers (max 100):
   - `<admin email>`
   - `<beta tester emails...>`
7. **SAVE AND CONTINUE** → **BACK TO DASHBOARD**

> ⚠️ Publishing status จะเป็น **"Testing"** — แปลว่าเฉพาะ email ใน Test users list เท่านั้นที่ใช้ได้.
> Refresh token หมดอายุทุก 7 วัน — user ต้อง re-connect Drive ทุกสัปดาห์.
> เหมาะกับ closed beta. หลัง public launch → submit verification (ดู [Verification](#-verification-mode-public-launch))

### Step 4 — OAuth Client ID (5 min)

1. **APIs & Services** → **Credentials**
2. **+ CREATE CREDENTIALS** → **OAuth client ID**
3. Application type: **Web application**
4. Name: `Personal Data Bank Web`
5. **Authorized JavaScript origins** (+ ADD URI):
   ```
   https://your-domain.com
   http://localhost:8000
   ```
6. **Authorized redirect URIs** (+ ADD URI — ต้องตรงเป๊ะ):
   ```
   https://your-domain.com/api/drive/oauth/callback
   http://localhost:8000/api/drive/oauth/callback
   ```
7. **CREATE**
8. 📋 **Popup จะแสดง 2 ค่า** — copy ลง password manager:
   ```
   Client ID:     ...apps.googleusercontent.com
   Client secret: GOCSPX-...
   ```

### Step 5 — API Key for Picker (3 min)

1. **Credentials** → **+ CREATE CREDENTIALS** → **API key**
2. 📋 **Popup แสดง:** `AIzaSy...` — copy ลง password manager
3. **CLOSE**
4. คลิกชื่อ API key ในตาราง → restrict (สำคัญ — กัน abuse):
   - **Application restrictions:** HTTP referrers
     ```
     https://your-domain.com/*
     http://localhost:8000/*
     ```
   - **API restrictions:** Restrict key → tick **Google Picker API**
5. **SAVE**

### Step 6 — Find Project Number (1 min)

1. คลิกชื่อ project มุมบน (ข้าง "Google Cloud" logo) → ดู panel ที่ popup
2. Copy **Project number** (~12 digits, e.g., `123456789012`)

> Note: Project number ≠ Project ID. Project number is numeric; Project ID is the slug.

---

## 🔑 Step 7 — Generate Encryption Key

Server จะ encrypt refresh tokens ก่อนเก็บใน DB. ต้องสร้าง Fernet key (ครั้งเดียวเท่านั้น):

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Output: `<44-char-base64-url-safe-fernet-key>` — โครงร่างเช่น `aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789aBcDeF=` (placeholder; ใช้ค่าจริงที่ generate เอง)

⚠️ **CRITICAL:** เก็บไว้ใน password manager + Fly.io secrets. **ห้ามทำหาย** — ถ้าหาย refresh_token ของลูกค้าทุกคนจะถอดไม่ออก = ลูกค้าทุกคนต้อง re-connect Drive

---

## ⚙️ Step 8 — Set Environment Variables

### Local development (`.env`)

```env
GOOGLE_OAUTH_CLIENT_ID=...apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-...
GOOGLE_PICKER_API_KEY=AIzaSy...
GOOGLE_PICKER_APP_ID=123456789012
GOOGLE_OAUTH_MODE=testing
DRIVE_TOKEN_ENCRYPTION_KEY=<PASTE_GENERATED_KEY_HERE>
```

### Fly.io production (secrets)

```bash
flyctl secrets set GOOGLE_OAUTH_CLIENT_ID="...apps.googleusercontent.com"
flyctl secrets set GOOGLE_OAUTH_CLIENT_SECRET="GOCSPX-..."
flyctl secrets set GOOGLE_PICKER_API_KEY="AIzaSy..."
flyctl secrets set GOOGLE_PICKER_APP_ID="123456789012"
flyctl secrets set GOOGLE_OAUTH_MODE="testing"
flyctl secrets set DRIVE_TOKEN_ENCRYPTION_KEY="<PASTE_GENERATED_KEY_HERE>"
flyctl deploy   # restart app to pick up new secrets
```

### Verify

```bash
curl https://your-domain.com/api/drive/status \
  -H "Authorization: Bearer $JWT" | jq

# Expected:
# {
#   "feature_available": true,    # was false before
#   "storage_mode": "managed",
#   "drive_connected": false,
#   "drive_root_folder_name": "Personal Data Bank",
#   "drive_schema_version": "1.0",
#   ...
# }
```

---

## 🧪 Test the Flow

1. Login เป็น user ที่อยู่ใน **Test users list**
2. Frontend (TBD ใน Phase 3) → click **"Connect Drive"**
3. Redirect ไป Google OAuth → consent → callback → return ที่หน้าหลัก
4. เปิด Drive → จะเห็น folder `/Personal Data Bank/` มี 7 sub-folders ใหม่
5. ลอง upload ไฟล์ผ่าน UI → check ว่าไฟล์ขึ้นใน `/Personal Data Bank/raw/`

---

## 🛡️ Security Best Practices

1. **Client Secret + API Key + Encryption Key = secrets**
   - เก็บใน password manager
   - ห้าม commit ลง git (`.env` already in `.gitignore`)
   - หมุน rotation ทุก 6-12 เดือน (ทำได้ใน Cloud Console → Credentials → click → Reset secret)
2. **Encryption Key**
   - **ห้ามทำหาย** — ทำหาย = users ทุกคนต้อง re-connect
   - Backup ใน 2-3 ที่ (password manager + offline)
3. **Test users restriction**
   - มี max 100 emails (Google enforced ใน Testing mode)
   - ไม่ปะปนกับ production users → ใช้ Sub-account สำหรับทดสอบ

---

## 🏆 Verification Mode (Public Launch)

หลัง MVP เสร็จ + พร้อมเปิดสาธารณะ → ขอ verification กับ Google เพื่อปลด Testing limits

### What changes
| | Testing Mode (now) | Production (verified) |
|---|---|---|
| Max users | 100 (manually added) | ไม่จำกัด |
| Refresh token expiry | 7 วัน | ไม่หมดอายุ |
| User warning | ไม่มี (เพราะอยู่ใน Test users) | ไม่มี |
| Privacy Policy | optional | required |
| Demo video | optional | required |
| Domain verification | optional | required |
| Cost | ฟรี | ฟรี (ถ้า scope = drive.file) |

### Materials needed
1. **Privacy Policy** → public URL `/privacy` (no login)
2. **Terms of Service** → public URL `/terms`
3. **Demo video** → 1-2 min YouTube unlisted, narrate in English
4. **Domain verification** → Google Search Console → add domain
5. **Scope justification** → 1-paragraph explaining `drive.file` use
6. **Submit** → Cloud Console → OAuth consent screen → **PUBLISH APP**

Review timeline: **2-4 weeks** (controllable ไม่ได้)

> 💡 Strategy: เริ่ม submit ทันทีหลัง MVP launch — ระหว่าง 2-4 weeks ที่รอ
> ก็ใช้ Testing Mode + Test users ทำ closed beta ไปก่อน

---

## ❓ Troubleshooting

### "App not verified" warning

✅ ปกติของ Testing Mode — กด **Advanced** → **Go to [App Name] (unsafe)** → ใช้งานต่อได้
- หลัง verification ผ่าน → warning หายอัตโนมัติ

### "redirect_uri_mismatch" error

❌ URI ใน app code ≠ URI ใน Cloud Console
- ตรวจ trailing slash (`/callback` vs `/callback/`)
- ตรวจ http vs https
- ตรวจ hostname (`localhost` vs `127.0.0.1` — ต้องตรงเป๊ะ)

### "Quota exceeded" / 429 errors

❌ Drive API rate limit (1000 req / 100s / user)
- App มี exponential backoff อยู่แล้ว — แค่รอ
- ถ้าโดนบ่อย → reduce sync frequency (default 5 min) ใน config

### Connection ตัดขาดหลังคืนกัน

❌ Refresh token หมดอายุ (Testing Mode = 7 วัน)
- User ต้อง click "Reconnect Drive" → re-grant consent
- แก้ถาวร: submit verification → switch to production mode

### "DRIVE_TOKEN_ENCRYPTION_KEY environment variable is missing"

❌ Server start แล้ว BYOS endpoints return 503 — ปกติ ถ้า env vars ไม่ครบ
- ตรวจว่า set 6 env vars ครบ (Step 8)
- restart app หลัง set secrets (`flyctl deploy`)

---

## 📚 Related

- Plan: [`.agent-memory/plans/google-drive-byos.md`](../.agent-memory/plans/google-drive-byos.md)
- Architecture: ดู section "📂 Drive Folder Structure" ใน plan
- Tests:
  - `scripts/byos_foundation_smoke.py` (26 tests, env var validation)
  - `scripts/byos_storage_smoke.py` (20 tests, CRUD round-trips)
  - `scripts/byos_sync_smoke.py` (24 tests, push/pull/conflict)
- Code:
  - [`backend/drive_oauth.py`](../backend/drive_oauth.py) — OAuth flow
  - [`backend/drive_storage.py`](../backend/drive_storage.py) — Drive CRUD
  - [`backend/drive_sync.py`](../backend/drive_sync.py) — sync engine
  - [`backend/drive_layout.py`](../backend/drive_layout.py) — folder constants
