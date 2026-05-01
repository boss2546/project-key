# 📖 PDB Project Overview

## โปรเจกต์คืออะไร
**Personal Data Bank (PDB)** เป็นพื้นที่ข้อมูลส่วนตัวที่ใช้ AI ช่วยจัดระเบียบ วิเคราะห์ และเชื่อมโยงข้อมูลของผู้ใช้

**Production:** https://project-key.fly.dev/ (Fly.io app name `project-key` ยังคงเดิม — รอ custom domain ภายหลัง)
**Current version:** 6.1.0 (rebrand) — deployed
**Next version:** 7.0.0 BYOS — in development on `byos-v7.0.0-foundation` branch

## เป้าหมายหลัก
- ผู้ใช้ upload ไฟล์ส่วนตัว (PDF, TXT, MD, DOCX) → AI จัดระเบียบให้อัตโนมัติ
- สร้าง Knowledge Graph เชื่อมโยงข้อมูลระหว่างไฟล์
- มีระบบ subscription (Stripe) แบ่งเป็น plans ต่างๆ
- เชื่อมต่อ MCP เพื่อให้ Claude/AI เข้าถึงข้อมูลผู้ใช้ได้
- **v7.0+:** ลูกค้าเลือกได้ว่าจะเก็บข้อมูลไว้ที่ server เรา หรือใน Google Drive ของตัวเอง (BYOS)

## ฟีเจอร์หลัก

**Live (v6.1.0):**
1. **My Data** — Upload + browse ไฟล์ (Managed Mode = server volume)
2. **AI Organizer** — จัดกลุ่ม + สรุป + สร้าง relations
3. **Knowledge View** — แสดงภาพรวม collections + graph
4. **MCP Integration** — 30 tools สำหรับ AI access (Claude/Antigravity/ChatGPT)
5. **Stripe Billing** — Plan limits, upgrade/downgrade, audit log
6. **Auth** — JWT-based authentication
7. **Context Packs** — รวมไฟล์เป็น pack ส่งให้ AI
8. **Personality Profile (v6.0)** — MBTI / Enneagram / CliftonStrengths / VIA + history
9. **Personal Data Bank rebrand (v6.1.0)** — display name + i18n + MCP serverInfo

**In development (v7.0.0):**
10. 🚧 **Google Drive BYOS** — ลูกค้าเลือก storage mode (managed | byos)
    - Phase 1-3 done: backend foundation + storage + sync + storage routing
    - Phase 4 pending: frontend UI + live OAuth E2E test + push + deploy
    - Architecture: Hybrid (Drive = source of truth, server = cache/index)

## ผู้ใช้เป้าหมาย
- บุคคลที่อยากเก็บ + จัดระเบียบข้อมูลส่วนตัวด้วย AI
- คนที่ใช้ Claude/AI tools และอยากให้ AI เข้าถึงข้อมูลตัวเองได้
- **v7.0+ users:** Privacy-conscious users ที่อยาก control ข้อมูลใน Drive ของตัวเอง

## ที่อยู่ของ Source Code
- Repo: d:\PDB\
- Backend: `/backend/` (Python FastAPI)
- Frontend: `/legacy-frontend/` (HTML/CSS/JS — ยังไม่ได้ migrate เป็น framework)
- Tests: `tests/test_*.py` + `tests/e2e-ui/*.spec.js` + `scripts/*_smoke.py` (in-process self-tests)
- Docs: `/docs/`, `/DESIGN.md`, `/README.md`, `/docs/BYOS_SETUP.md` (v7.0)

## สถานะปัจจุบัน
- ✅ Production live แล้ว at https://project-key.fly.dev/ (v6.0.0 — Personality Profile)
- 🟡 v6.1.0 Rebrand: review_passed, pending merge + deploy
- 🟢 v7.0.0 BYOS: Phase 3/4 done, ฟ้า takes over for Phase 4 (frontend + live test + push)
- ✅ Stripe integration ทำงานได้
- ✅ Smoke test suite (182/182 in-process tests) pass 100%
- 🚧 Frontend ยังเป็น legacy (HTML+JS) ยังไม่ได้ migrate เป็น React/Vue (per FE-001 decision)

## สถาปัตยกรรม BYOS (v7.0 preview)

```
┌─────────────────────────────────────────────────────────────┐
│ User's Google Drive (Source of truth — when storage_mode=byos) │
│ /Personal Data Bank/                                          │
│   ├── raw/         original files                            │
│   ├── extracted/   plain text                                │
│   ├── summaries/   AI markdown                               │
│   ├── personal/    profile.json + contexts.json              │
│   ├── data/        clusters/graph/relations/chat_history.json │
│   ├── _meta/       schema version + manifest                 │
│   └── _backups/    weekly snapshots                          │
└─────────────────────────────────────────────────────────────┘
                            ↕ sync (poll every 5 min + on-write)
┌─────────────────────────────────────────────────────────────┐
│ PDB Server (Cache + Index)                                   │
│ SQLite — เก็บแค่:                                            │
│   • user account + OAuth refresh_token (encrypted)           │
│   • storage_mode = "managed" | "byos"                        │
│   • drive_connection (drive_email, last_sync_at)             │
│   • files index (file_id ↔ drive_file_id, hash, modified)    │
│   • vector embeddings (rebuildable from Drive)               │
│   • personality cache, graph cache                           │
└─────────────────────────────────────────────────────────────┘
```

ดู [`docs/BYOS_SETUP.md`](../../docs/BYOS_SETUP.md) สำหรับ admin setup walkthrough.
