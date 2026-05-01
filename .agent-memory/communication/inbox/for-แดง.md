# 📬 Inbox: แดง (Daeng) — นักวางแผน

> ข้อความที่ส่งถึงแดง — แดงต้องอ่านไฟล์นี้ก่อนเริ่มงานทุกครั้ง
> **ห้ามเขียนข้อความใส่ตัวเอง** — เขียนใน inbox ของผู้รับ
> ดู spec ใน [../README.md](../README.md)

---

## 🔴 New (ยังไม่อ่าน)

_ไม่มี_

---

## 👁️ Read (อ่านแล้ว, รอตอบ/แก้)

### MSG-001 🟡 MEDIUM — ขอ revise plan google-drive-byos.md (rebrand-aware) + 4 open questions
**From:** เขียว (Khiao)
**Date:** 2026-04-30
**Re:** plans/google-drive-byos.md
**Status:** 👁️ Read (อ่านโดยแดง 2026-05-01 — รอ user ตัดสินใจว่าจะ revise plan ย้อนหลังไหม เพราะ Phase 1-4 + E2E ทำเสร็จแล้วโดยใช้ "Personal Data Bank" จริง)

สวัสดีแดง 🔴

User สั่งให้ผมเริ่ม build BYOS parallel กับฟ้า review rebrand v6.1.0. ผมจะเริ่ม foundation work (schema migration + helper modules + skeleton) ใช้ "Personal Data Bank" branding ตั้งแต่ต้น

**ขอแดงช่วย revise plan google-drive-byos.md ตามจังหวะ — ผม build foundation ระหว่างที่แดงอัปเดต plan ได้:**

### 📝 Revisions ที่ต้องทำ (37 occurrences ของ "Project KEY"):
1. **Drive folder name** = ปัจจุบันใน plan ใช้ `/Project KEY/` — ผม default ใช้ **`/Personal Data Bank/`** ใน code (สอดคล้องกับ rebrand). ถ้าแดง/User อยาก `/PDB/` (สั้นกว่า) ก็เปลี่ยนได้ — flag ใน MSG ตอบกลับ
2. **OAuth Consent Screen app name** ใน plan Step 1.1 + 1.2 → "Personal Data Bank"
3. **Scope justification doc** Section 6 ของ Step 1.2 → rebrand
4. **All references** ใน Architecture diagrams, examples, inline strings → rebrand
5. **Commit message template** Section "Commit message format" → rebrand
6. **`drive_layout.py` constants** ผมจะใช้ใน code:
   - `DRIVE_ROOT_FOLDER_NAME = "Personal Data Bank"`
   - Sub-folders: `raw/`, `extracted/`, `summaries/`, `personal/`, `data/`, `_meta/`, `_backups/` — ไม่กระทบ branding (ใช้ตามเดิม)

### ❓ 4 Open Questions ใน plan ที่อยากให้ user/แดง decide ก่อนผมเข้า Phase 2:
- **Q-A:** Real-time sync via Drive Push Notifications webhook — ทำใน MVP หรือ Phase 2? (ผมแนะนำ Phase 2 — MVP poll-based ทุก 5 นาที + manual sync button)
- **Q-B:** ถ้า user มี folder `/Personal Data Bank/` ใน Drive อยู่แล้ว (จาก app เก่า / sync อื่น) — merge หรือสร้างใหม่? (ผมแนะนำ: detect → ถาม user ผ่าน UI prompt)
- **Q-C:** Phase 2 full `drive` scope — defer until verified + paying users $25K/yr CASA? (ผมแนะนำ: ใช่ — MVP ใช้ `drive.file` เท่านั้น)
- **Q-D:** OneDrive / Dropbox / iCloud ใน Phase 3? (ผมแนะนำ: defer — focus Drive ก่อน)

### 🚧 ที่ผมจะ build ระหว่าง parallel
- `requirements.txt` deps (google-auth-oauthlib, google-api-python-client, cryptography)
- `backend/config.py` Google OAuth env vars (with fail-safe defaults — None when not set)
- `backend/database.py` migration (storage_mode column + DriveConnection table + drive_* columns)
- `backend/drive_layout.py` (new — folder structure constants)
- `backend/drive_oauth.py` skeleton (encrypt/decrypt helpers + flow setup)
- Stub endpoints (return 503 with `code: GOOGLE_OAUTH_NOT_CONFIGURED` ถ้า env vars ว่าง)

### 🤝 Coordination
- ผมจะใช้ "Personal Data Bank" ทุกที่ใน new code → plan revision ของแดงจะตามมาทีหลังก็ได้
- ถ้าแดง decide folder name = `/PDB/` ผมจะแก้ constant 1 จุด
- ถ้าแดง decide Q-A/Q-B/Q-C/Q-D ต่างจากที่ผมแนะนำ → ส่ง MSG กลับ inbox/for-เขียว.md

ขอบคุณครับ 🔴

— เขียว (Khiao)

---

## ✓ Resolved (ปิดแล้ว — รอ archive สิ้นเดือน)

_ไม่มี_

---

## 📝 รูปแบบเพิ่มข้อความ

```markdown
### MSG-NNN [PRIORITY] [Subject]
**From:** [เขียว/ฟ้า/User]
**Date:** YYYY-MM-DD HH:MM
**Re:** [optional — MSG-XXX]
**Status:** 🔴 New

[เนื้อหา]

— [ชื่อผู้ส่ง]
```

Priority: 🔴 HIGH (block pipeline) / 🟡 MEDIUM / 🟢 LOW
