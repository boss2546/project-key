# 🎯 Active Tasks

> Source of truth คือ [pipeline-state.md](pipeline-state.md) — ไฟล์นี้เป็น overview
> Pipeline ตอนนี้ = `plan_pending_approval` (v7.2.0 UX Hotfixes — รอ user approve plan)

---

## 🔄 Current Pipeline

### 🔴 v7.2.0 — UX Critical Hotfixes (`plan_pending_approval`)
**Plan file:** [plans/ux-hotfixes-v7.2.0.md](../plans/ux-hotfixes-v7.2.0.md)
**Author:** แดง (Daeng) — 2026-05-02
**Priority:** 🔴 Critical (Data integrity + system stability) — user สั่งข้ามคิว
**Estimated effort:** เขียว ~2-3 ชม. + ฟ้า ~1 ชม.

**5 Sections:**
1. Button Loading States — disabled + spinner สำหรับ saveProfile + sendMessage
2. Upload Progress — XHR progress + beforeunload guard
3. Error Toast — type='error' ห้าม auto-dismiss + ปุ่ม X
4. AI Typing Indicator — `<span id="chat-typing-status">` ทันทีตอนกด send
5. Modal UX — global ESC + backdrop click (8 modals ใน app)

**Pending action:** User approve plan → state เปลี่ยน → เขียวเริ่ม build

---

## ✅ Recently Shipped (เรียงจากใหม่ไปเก่า)

งาน v6.0.0 / v6.1.0 / v7.0.0 / v7.0.1 / v7.1.0 ทั้งหมด deployed บน master แล้ว — ดูรายละเอียดในส่วน "Completed Features" ด้านล่าง

---

## 🚨 Pre-Launch Backlog (สำคัญ — ต้องทำก่อน public launch)

- [ ] **[BACKLOG-008] 🔴 Restore plan_limits.py production values**
  - Priority: 🔴 HIGH (block public launch — ตอนนี้ทุก plan = 999999 ทุก field)
  - Estimated effort: S (~30 min — แก้ค่า + bump test fixtures + deploy)
  - Reference: ค่าเดิมก่อน testing-mode neuter อยู่ใน commit `d8b0d54` diff
  - Original values:
    ```python
    "free": {
      "context_pack_limit": 1, "file_limit": 5, "storage_limit_mb": 50,
      "max_file_size_mb": 10, "ai_summary_limit_monthly": 5,
      "export_limit_monthly": 10, "refresh_limit_monthly": 0,
      "semantic_search_enabled": False, "version_history_days": 0,
      "allowed_file_types": {"pdf", "docx", "txt", "md", "csv"},
    },
    "starter": {
      "context_pack_limit": 5, "file_limit": 50, "storage_limit_mb": 1024,
      "max_file_size_mb": 20, "ai_summary_limit_monthly": 100,
      "export_limit_monthly": 300, "refresh_limit_monthly": 10,
      "semantic_search_enabled": True, "version_history_days": 7,
      "allowed_file_types": {"pdf", "docx", "txt", "md", "csv", "png", "jpg"},
    },
    ```
  - File: [backend/plan_limits.py:15-42](../../backend/plan_limits.py#L15-L42)
  - User decide ก่อนทำ: ใช้ค่าเดิม หรือ revise (พ่วง pricing strategy)

- [ ] **[BACKLOG-009] 🔴 Wire email service for password reset (Phase 2)**
  - Priority: 🔴 HIGH (block public launch — ตอนนี้ return reset_token ใน JSON ตรงๆ)
  - Estimated effort: M (~3-4 hr — choose service + integration + drop token from response + smoke test)
  - Files: [backend/auth.py:249-282](../../backend/auth.py#L249-L282)
  - **User decide:** เลือก email service ก่อนทำ
    - 🟢 **Resend** (แนะนำ): free 3000/เดือน, modern API, simple Python SDK
    - 🟡 SendGrid: free 100/วัน, mature, มี Python SDK
    - 🟡 Gmail SMTP: ฟรีจริง แต่ deliverability + rate limits ไม่ดีเท่า dedicated
  - Tasks หลังเลือก service:
    1. เพิ่ม `RESEND_API_KEY` (หรือเทียบเท่า) ใน `.env.example` + Fly.io secrets
    2. เขียน helper `send_password_reset_email(email, reset_link)` ใน new `backend/email.py`
    3. แก้ `request_password_reset()` ให้เรียก helper + drop `reset_token` จาก response
    4. Add Privacy Policy + Terms of Service URL (สำหรับ unsubscribe link)

---

## 📋 Long-term Backlog (deferred ตามเดิม)

- [ ] [BACKLOG-001] BYOS multi-account (personal + work Drive per user)
  - Priority: 🟢 Low (Phase 2 of BYOS roadmap)
  - Estimated effort: M
- [ ] [BACKLOG-002] Real-time sync via Drive Push Notifications webhook
  - Priority: 🟢 Low (currently using poll-based 5-min sync)
  - Estimated effort: M
- [ ] [BACKLOG-003] Full `drive` scope (CASA verification $25K-85K/yr)
  - Priority: 🟢 Low (defer to revenue threshold)
  - Estimated effort: L (incl. verification submission)
- [ ] [BACKLOG-004] BYOS for OneDrive / Dropbox / iCloud
  - Priority: 🟢 Low (Phase 3+)
  - Estimated effort: L per provider
- [ ] [BACKLOG-005] Custom domain (replace `personaldatabank.fly.dev`)
  - Priority: 🟢 Low (deferred)
  - Estimated effort: S (DNS) + M (rotate URL refs)
- [ ] [BACKLOG-006] OAuth verification submission for Google production mode
  - Priority: 🟡 Medium (unblock public launch — pairs with BACKLOG-008/009)
  - Estimated effort: M (Privacy Policy + Demo video + scope justification)
- [ ] [BACKLOG-007] Frontend migration to React/Vue
  - Priority: 🟢 Low (per FE-001 decision — defer)
  - Estimated effort: L

---

## ✅ Completed Features

- [x] **v7.1.0 — Duplicate Detection on Organize-new** (2026-05-01)
  - Plan: [plans/duplicate-detection.md](../plans/duplicate-detection.md)
  - Built by: เขียว (round 1 + pivot DUP-003)
  - Reviewed by: ฟ้า (REVIEW-002, APPROVE 87/87 + 106/106 regression)
  - Merged: master `cd114dd`, `0adcaf1`, `c047657`, `6467b3a`

- [x] **v7.0.0 → v7.0.1 — Google Drive BYOS** (2026-05-01 deploy + 5 follow-up fixes)
  - Plan: [plans/google-drive-byos.md](../plans/google-drive-byos.md)
  - Built by: เขียว Phase 1-3 + ฟ้า Phase 4 + E2E (full dev mode authority)
  - Deployed: Fly.io machine 82, 2026-05-01 03:04 UTC
  - Follow-ups: `73f1a96` (raw push), `e1908b8`, `ac9a6e3`, `1449666`, `c04d21c` (sync fixes)

- [x] **v6.1.0 — PDB Rebrand "Project KEY" → "Personal Data Bank"** (2026-04-30 → 2026-05-01)
  - Plan: [plans/rebrand-pdb.md](../plans/rebrand-pdb.md)
  - Built by: เขียว (5 commits + 76/76 smoke pass)
  - Reviewed by: ฟ้า (APPROVE + version drift fix `1b7fd98`)
  - Merged: master `6e14e63`, then `d2f92da` (localStorage), `0182c06` (domain), `ee8699d` (Fly.io app)

- [x] **v6.0.0 — Personality Profile (MBTI/Enneagram/Clifton/VIA + History)** (2026-04-30)
  - Plan: [plans/personality-profile.md](../plans/personality-profile.md)
  - Built by: เขียว
  - Reviewed by: ฟ้า
  - Merged: 2026-04-30 (commit `3f4b4b9`)

---

## ⚠️ ระบบ Pipeline ทำงานยังไง

```
Default sequential (1 feature at a time):
1. User เลือก feature จาก backlog
2. แดง วาง plan
3. User approve plan
4. เขียว build code
5. ฟ้า review + tests
6. User approve review
7. Merge → ย้ายไป Completed

Parallel override (per user — ใช้ตอน v6.1.0 + v7.0.0):
- 2 features in pipeline simultaneously
- Different agents own different features
- Authority extended (e.g., ฟ้า can dev + commit + push without review-back)
```

Default = sequential. Parallel = explicit user override only.
