# 🔄 Pipeline State

> **ไฟล์สำคัญที่สุด** — บอกว่า feature ปัจจุบันถึงไหนแล้วใน pipeline
> ทุก agent ต้องอ่านก่อนเริ่มทำงาน + update เมื่อเสร็จงาน

---

## 🎯 Current State: `idle` 🟢 (no active feature in pipeline)

**Master HEAD:** `7a2f84a` (v9.4.8 · 2026-05-12 08:54 +07)
**APP_VERSION:** **9.4.8**
**Production:** ✅ **v9.4.8 deployed live** ที่ `https://personaldatabank.fly.dev`
- Worker uptime ~11 นาที (เพิ่ง deploy v9.4.8) · queue ว่าง · success_24h = 100% · error_24h = 0
- avg_extract_sec_by_class: class 1 = 1.0s · class 2 = 13.27s · class 3 = 74.29s (post-cap healthy)

**Mode:** ปัจจุบันไม่มี feature ใน pipeline · pipeline state = idle · พร้อมรับงานใหม่

---

## ⚠️ Pipeline drift notice (2026-05-11 → 2026-05-12)

**Memory ไฟล์เคย stale หลายรอบ** — sync ใหม่ 2026-05-12 (ฟ้า) ให้ตรง master HEAD จริง.

**Session gap:** ระหว่าง 2026-05-10 ถึง 2026-05-12 มี **8 versions shipped ใน 3-in-1 mode** (user รันตรงผ่าน Claude Code Opus 4.7 1M context · ไม่ผ่าน sequential pipeline แดง→เขียว→ฟ้า · เห็นจาก commit `Co-Authored-By` trailer):

| Version | Commit | Date | Scope |
|---|---|---|---|
| v9.4.0 | `aa26ed2` … `ee07e27` (~7 commits) | 2026-05-10 | Upload Queue + Visible Progress (worker · UI tray · 4 endpoints · WAL) |
| v9.4.0.1 | `2c93a1d` | 2026-05-10 | UI hotfix · tray position + toast text |
| v9.4.0.2 | `d81369c` | 2026-05-10 | UI hotfix · opaque BG + suppress queue toast |
| v9.4.1 | `a314a42` | 2026-05-10 | Comprehensive Drive cleanup async + UI feedback |
| v9.4.2 | `f45ab96` | 2026-05-10 | Gemini 2.5 Flash + Vision + truthful classification |
| v9.4.3 | `c738ff0` | 2026-05-10 | LINE UX 5 fixes + nonce + countdown timer |
| v9.4.4 | `f2e707e` | 2026-05-10 | i18n error CODE boundary + reprocess hardening |
| v9.4.5 | `015628c` | 2026-05-10 | Worker heartbeat task + startup recovery + cancel endpoint |
| v9.4.6 | `9f94765` | 2026-05-11 | Progress+cancel main loop ref + always-on Cancel button |
| v9.4.7 | `e658c74` | 2026-05-11 | Filename 255-byte ext4 limit (Thai filename UTF-8 overflow fix) |
| v9.4.8 | `7a2f84a` | 2026-05-12 | DELETE guard + ai_pack filter + rolling avg cap |

**Status ของ formal ฟ้า review:** ❌ ไม่มี · `MSG-V940-UPLOAD-QUEUE` ใน `inbox/for-ฟ้า.md` ยังค้างใน 🔴 New แต่ของ deploy + ใช้งานจริงไป 11 versions แล้ว · gap นี้ยอมรับเป็น operational reality.

---

## 📋 Known unresolved issues (จาก audit 2026-05-12 by ฟ้า)

| # | Issue | Severity | Status |
|---|---|---|---|
| **P9** | Duplicate detection disabled ตั้งแต่ v9.3.2 — `_DEDUP_DISABLED = True` ใน `backend/duplicate_detector.py` | 🟡 MED | BACKLOG-009 · pending re-enable + pytest case |
| **P5** | Untracked files หลายกลุ่มใน working tree (smoke scripts ใหม่ · screenshots · `data/`/`datame/`) | 🟡 MED | Track A2/A3 (in progress) |
| **P4** | v9.4.2/4/5/6/7/8 ไม่มี plan files (shipped ใน 3-in-1 mode) | 🟢 LOW | Defer · ไม่กระทบ production · ทำ retro changelog ถ้าจำเป็น |
| **P1** | v9.4.0 Truthfulness Contract TC-1..6 ไม่เคย E2E audit · ของ deploy แล้ว · worker health green | 🟢 LOW | Defer · prod stable 24h+ · ทำตอนแตะ upload pipeline รอบหน้า |

**ที่เคยอยู่ใน Issue list · resolved แล้ว:**
- ✅ **P7 (PDF 219.6s slow)** — v9.4.8 rolling avg cap (class 2: 60s outlier cap) · prod stat ลด 219.6 → 13.27s
- ✅ **P3 (pipeline-state stale)** — sync วันนี้ (ไฟล์ที่คุณกำลังอ่าน)

---

## 📜 Reference — historical state snapshots

ก่อนหน้า v9.4.x · pipeline เคยอยู่ใน sequential mode ปกติ (แดง→เขียว→ฟ้า). ดู git log สำหรับ chronology + ดู `plans/` archive สำหรับ formal plans ที่ shipped:

- v9.3.5 BYOS Reconnect UX FINAL — เป็น last formal sequential pipeline pass (ฟ้า re-review APPROVE 2026-05-10)
- v9.3.4 LLM/AI surrogate boundary — 3-in-1 mode
- v9.3.3 extraction surrogate guard — 3-in-1 mode
- v9.3.2 disable duplicate detection — 3-in-1 mode (current BACKLOG-009)
- v9.3.0 Phase A-E UI foundation + Share Pack — sequential
- v9.2.0 AI Pack Builder — sequential
- v9.1.0 Raw File Vault — sequential
- v9.0.1 Context Pack correctness — 3-in-1 mode
- v8.x line bot + admin + google login — sequential

---

**Last sync:** 2026-05-12 by 🔵 ฟ้า (Track A1 · pipeline-state drift fix)
