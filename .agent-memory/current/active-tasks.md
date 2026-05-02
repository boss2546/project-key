# 🎯 Active Tasks

> Source of truth คือ [pipeline-state.md](pipeline-state.md) — ไฟล์นี้เป็น overview
> Pipeline ตอนนี้ = `idle` (รอ user มอบหมายงานใหม่)

---

## 🔄 Current Pipeline

**State:** `idle` — งาน v7.4.0 เป็น feature ล่าสุดที่ shipped บน master (2026-05-02)

ไม่มี feature active ใน pipeline — รอ user มอบหมายงานใหม่ หรือสั่ง deploy v7.1.5+v7.2/v7.3/v7.4 ขึ้น production

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

## 🚀 Pending Production Deploy

**Master HEAD:** `b8e8014` v7.4.0 SaaS responsive
**Production (Fly.io):** v7.1.0
**Gap:** 17 commits — รวม v7.1.5 + v7.2.0 + v7.3.0 + v7.4.0 + cleanup

ทำเสร็จบน master แต่ user ยังไม่เห็น — รอ `flyctl deploy -a personaldatabank`

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

## ✅ Completed Features (เรียงจากใหม่ไปเก่า)

- [x] **v7.4.0 — SaaS Responsive Design & Mobile UX** (2026-05-02)
  - Plan: [archive/2026-05-02-saas-responsive-v7.4.0.md](../plans/archive/2026-05-02-saas-responsive-v7.4.0.md)
  - 4 fixes: Touch Targets 44px / Page FAB / File List Card View / Context Memory Kebab
  - Tests: 14 v7.4.0 + 103 frontend regression + 52 backend pytest = 169/169 PASS
  - Commit: `b8e8014`

- [x] **v7.3.0 — UX Edge-Cases & Mobile Fixes** (2026-05-02)
  - Plan: [archive/2026-05-02-ux-edgecases-v7.3.0.md](../plans/archive/2026-05-02-ux-edgecases-v7.3.0.md)
  - 3 fixes: Mobile Responsive (sidebar) / Form Validation / Z-index Hierarchy
  - Tests: 14 v7.3.0 + 89 regression = 103 PASS
  - Commit: `62968c6`

- [x] **v7.2.0 — UX Critical Hotfixes** (2026-05-02)
  - Plan: [archive/2026-05-02-ux-hotfixes-v7.2.0.md](../plans/archive/2026-05-02-ux-hotfixes-v7.2.0.md)
  - 5 fixes: Button Loading / Upload Progress / Error Toast / AI Typing / Modal UX
  - Tests: 12 v7.2.0 + 89 regression = 101 PASS
  - Commit: `de34f8f`

- [x] **v7.1.5 — Dedupe UX Quick Wins** (2026-05-02)
  - Plan: [archive/2026-05-02-dedupe-ux-v7.1.5.md](../plans/archive/2026-05-02-dedupe-ux-v7.1.5.md)
  - 2 fixes: Per-file action in popup / Undo toast 10s + X dismiss
  - 3-in-1 mode (single agent full pipeline)
  - Tests: 183/183 regression PASS
  - Commit: `1fb7f40`

- [x] **v7.1.0 — Duplicate Detection on Organize-new** (2026-05-01)
  - Plan: [archive/2026-05-01-duplicate-detection.md](../plans/archive/2026-05-01-duplicate-detection.md)
  - Built by: เขียว (round 1 + pivot DUP-003)
  - Reviewed by: ฟ้า (REVIEW-002, APPROVE 87/87 + 106/106 regression)
  - Merged: master `cd114dd`, `0adcaf1`, `c047657`, `6467b3a`

- [x] **v7.0.0 → v7.0.1 — Google Drive BYOS** (2026-05-01 deploy + 5 follow-up fixes)
  - Plan: [archive/2026-05-01-google-drive-byos.md](../plans/archive/2026-05-01-google-drive-byos.md)
  - Built by: เขียว Phase 1-3 + ฟ้า Phase 4 + E2E (full dev mode authority)
  - Deployed: Fly.io machine 82, 2026-05-01 03:04 UTC
  - Follow-ups: `73f1a96` (raw push), `e1908b8`, `ac9a6e3`, `1449666`, `c04d21c` (sync fixes)

- [x] **v6.1.0 — PDB Rebrand "Project KEY" → "Personal Data Bank"** (2026-04-30 → 2026-05-01)
  - Plan: [archive/2026-05-01-rebrand-pdb.md](../plans/archive/2026-05-01-rebrand-pdb.md)
  - Built by: เขียว (5 commits + 76/76 smoke pass)
  - Reviewed by: ฟ้า (APPROVE + version drift fix `1b7fd98`)
  - Merged: master `6e14e63`, then `d2f92da` (localStorage), `0182c06` (domain), `ee8699d` (Fly.io app)

- [x] **v6.0.0 — Personality Profile (MBTI/Enneagram/Clifton/VIA + History)** (2026-04-30)
  - Plan: [archive/2026-04-30-personality-profile.md](../plans/archive/2026-04-30-personality-profile.md)
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

Single-agent 3-in-1 mode (per user authorization — ใช้ตอน v7.1.5):
- 1 agent ทำทั้ง plan + build + review (ไม่มี inter-session reload)
```

Default = sequential. Parallel + 3-in-1 = explicit user override only.
