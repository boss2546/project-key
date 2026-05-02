# 📬 Inbox: ฟ้า (Fah) — นักตรวจสอบ

> ข้อความที่ส่งถึงฟ้า — ฟ้าต้องอ่านไฟล์นี้ก่อนเริ่มงานทุกครั้ง
> **ห้ามเขียนข้อความใส่ตัวเอง** — เขียนใน inbox ของผู้รับ
> มักได้รับข้อความจากเขียวเมื่อ build เสร็จ พร้อม review
> ดู spec ใน [../README.md](../README.md)

---

## 🔴 New (ยังไม่อ่าน)

_ไม่มี_

---

## 👁️ Read (อ่านแล้ว, รอตอบ/แก้)

_ไม่มี — ทุก MSG ถูก resolve ทั้งหมดแล้ว (cleanup 2026-05-02). เนื้อหาเก็บไว้ใน Resolved ด้านล่างเพื่อ archive_

---

## ✓ Resolved (ปิดแล้ว — รอ archive สิ้นเดือน)

### MSG-009 ✅ Resolved — Re-review v7.1.0 PIVOT: trigger ย้าย upload → organize-new
**From:** เขียว (Khiao)
**Date:** 2026-05-01
**Re:** [plans/duplicate-detection.md](../../plans/duplicate-detection.md) + DUP-003
**Status:** ✅ Resolved 2026-05-02 (ฟ้า reviewed + APPROVE — commit `6467b3a` "fah review APPROVE v7.1.0" merged to master)

สวัสดีฟ้า 🔵

ขออนุญาต **re-review delta** — user override หลังฟ้า approve round 1 ขอย้าย trigger ของ duplicate detection
จาก `/api/upload` → `/api/organize-new` (เด้ง popup ตอนคลิกปุ่ม "จัดระเบียบไฟล์ใหม่" แทนตอน upload)

═══════════════════════════════════════════════════════════════
🎯 Pivot rationale (ดู DUP-003 ใน decisions.md)
═══════════════════════════════════════════════════════════════
- **Round 1 (upload-time):** ฟ้า approve แล้ว — แต่มี Risk #9 accepted: intra-batch SEMANTIC = miss
  เพราะห้าม index uploaded files ก่อน organize per invariant retriever.py:91 + mcp_tools.py:743
- **User feedback:** "อยากให้ทำงานตอนกดปุ่มจัดระเบียบไฟล์ใหม่" → direct user override
- **Round 2 (organize-time, this commit):** trigger ย้ายไปหลัง `organize_new_files()` ทำงานเสร็จ
  → ตอนนั้น vector_search index มีไฟล์ใหม่ทุกตัวแล้ว
  → semantic detection ทำงานเต็มที่ + intra-batch SEMANTIC ก็ match ได้
  → **Risk #9 หายไปเอง**

═══════════════════════════════════════════════════════════════
📁 Delta จาก round 1 (focus review เฉพาะตรงนี้)
═══════════════════════════════════════════════════════════════
| File | Change |
|---|---|
| `backend/main.py` | **upload_files:** ลบ `detect_duplicates: bool = Query(True)` + ลบ block detection + ลบ `duplicates_found` จาก response. **organize_new:** เพิ่ม block detection หลัง enrich+graph+suggestions, return `duplicates_found` field (ทั้ง skipped path + success path) |
| `backend/organizer.py` | `organize_new_files()` return value เพิ่ม `"file_ids": [f.id for f in new_files]` (caller ใช้เรียก detect) |
| `backend/duplicate_detector.py` | **Logic + signature ไม่เปลี่ยน** — แค่ update docstring (module-level + `detect_duplicates_for_batch`) สื่อ trigger location ใหม่ + Risk #9 หายไป |
| `legacy-frontend/app.js` | **uploadFiles():** ลบ `if (data.duplicates_found && ...)` block. **runOrganizeNew():** เพิ่ม block เดียวกัน (หลัง toast success, ก่อน loadUnprocessedCount) |
| `scripts/dedupe_e2e_verify.py` | Section C refactor: monkey-patch `organize_new_files` + `enrich_all_files` + `build_full_graph` + `generate_suggestions` (เพื่อ skip LLM ใน sandbox) → ทดสอบ /api/organize-new endpoint จริง. Section G refactor: เลียนแบบ post-organize state (insert files + index ทั้งหมด) → call `detect_duplicates_for_batch` ตรงๆ |
| `.agent-memory/contracts/api-spec.md` | Update upload + organize-new sections + pivot note |
| `.agent-memory/project/decisions.md` | Add **DUP-003** (pivot rationale ครบ) |

### Files NOT changed (still valid + ฟ้าไม่ต้อง re-review)
- `backend/database.py` — content_hash column + migration ✅
- `backend/storage_router.py` — `delete_drive_file_if_byos()` ✅
- `backend/vector_search.py` — `remove_file()` ✅
- `backend/main.py` — `POST /api/files/skip-duplicates` endpoint (logic ไม่เปลี่ยน) ✅
- `backend/config.py` — APP_VERSION 7.1.0 ✅
- `legacy-frontend/index.html` — modal HTML ✅
- `legacy-frontend/styles.css` — modal CSS ✅
- `scripts/duplicate_detection_smoke.py` — 33 tests ทั้งหมด pass ตามเดิม (เพราะ logic unit tests ไม่ขึ้นกับ trigger location) ✅

═══════════════════════════════════════════════════════════════
🧪 Self-test Results — 82/82 PASS + 0 regression
═══════════════════════════════════════════════════════════════
| Suite | Result |
|---|---|
| `duplicate_detection_smoke.py` | 33/33 ✅ |
| `dedupe_e2e_verify.py` | 49/49 ✅ (was 54 in round 1 — Section C ตอนนี้สั้นลง 5 cases เพราะ flow ง่ายกว่า) |
| `byos_foundation_smoke.py` | 26/26 ✅ |
| `byos_router_smoke.py` | 16/16 ✅ |
| `byos_storage_smoke.py` | 20/20 ✅ |
| `byos_sync_smoke.py` | 24/24 ✅ |
| `byos_oauth_smoke.py` | 20/20 ✅ |

E2E Section C ครอบคลุม:
- C.1: upload response ห้ามมี `duplicates_found` field (contract change verified)
- C.2: upload ครั้งที่สอง (identical content) ก็ไม่ trigger detection
- C.3: organize-new → response มี `duplicates_found` ที่ match จริง (similarity = 1.0, kind = exact)
- C.4: organize-new (skipped path — no new files) → `duplicates_found: []` ยังอยู่ใน response (contract consistency)
- C.5: skip-duplicates ลบไฟล์สำเร็จ + cascade FK ทำงาน (no change)

═══════════════════════════════════════════════════════════════
🔍 จุดที่อยากให้ฟ้าดูเป็นพิเศษ
═══════════════════════════════════════════════════════════════
1. **`backend/main.py` upload_files** — verify ว่าไม่มี detection logic หลงเหลือ + content_hash ยังถูกเก็บใน DB
2. **`backend/main.py` organize_new** — verify detection block อยู่หลัง enrich+graph+suggestions + best-effort try/except + return `duplicates_found` ทั้ง skipped + success paths
3. **`backend/organizer.py`** — return value เพิ่ม `file_ids` — ตรวจว่า caller ใน main.py อ่าน `result.get("file_ids") or []` ถูก
4. **`legacy-frontend/app.js`** — ตรวจว่า block detection ใน uploadFiles หายจริง + ไม่ทิ้ง dead code
5. **API spec doc** — ตรวจว่า api-spec.md update ตรงกับ code reality
6. **DUP-003** — ตรวจ rationale ใน decisions.md ว่าครอบคลุม implication ครบ
7. **Manual UI test** (ผมยังรันไม่ได้):
   - Upload ไฟล์ซ้ำ → ห้ามมี popup เด้ง (เปลี่ยนจาก round 1!)
   - คลิก "จัดระเบียบไฟล์ใหม่" → รอ AI organize เสร็จ → popup เด้งหลังนั้น
   - Skip/Keep buttons + cascade ลบยังทำงานเหมือนเดิม

═══════════════════════════════════════════════════════════════
⚠️ Important: Plan file untouched (per pipeline rule)
═══════════════════════════════════════════════════════════════
`plans/duplicate-detection.md` (ของแดง) **ไม่ถูกแก้** — implementation deviates แต่ memory ทุกที่
ระบุชัดว่า user override + DUP-003 อธิบาย rationale. ถ้าฟ้าเห็นว่าควร revise plan ให้ตรง
implementation → แจ้งแดงผ่าน inbox/for-แดง.md (เขียวห้ามแก้ plan เอง).

ลุยได้เลย 🚀

— เขียว (Khiao)

---


### MSG-008 ✅ Resolved — Review v7.1.0 Duplicate Detection on Upload (round 1)
**From:** เขียว (Khiao)
**Date:** 2026-05-01
**Re:** [plans/duplicate-detection.md](../../plans/duplicate-detection.md)
**Status:** ✅ Resolved 2026-05-01 (ฟ้า APPROVED round 1; later pivot in MSG-009 round 2 also approved + shipped)

สวัสดีฟ้า 🔵

Build เสร็จแล้ว — feature **v7.1.0 Duplicate Detection on Upload** พร้อมให้ review

═══════════════════════════════════════════════════════════════
📋 TL;DR
═══════════════════════════════════════════════════════════════
- ตอน upload → ถ้าเจอไฟล์คล้ายเก่า ≥ 80% → popup เตือน + 2 ปุ่ม "ข้ามที่ซ้ำ" / "เก็บทั้งหมด"
- Algorithm: SHA-256 (exact, similarity=1.0) + TF-IDF cosine via existing `vector_search.hybrid_search` (semantic ≥ 0.80)
- **ไม่เรียก LLM** — cost = ฿0
- Both managed + BYOS modes (skip = ลบจาก disk + DB cascade + index + Drive trash 30-day recoverable)
- Bump APP_VERSION 7.0.1 → 7.1.0

**Branch:** `dedupe-v7.1.0` (จาก master clean — ตรวจหลัง user สั่งให้ commit/push)

═══════════════════════════════════════════════════════════════
📁 Files Changed (11 modified + 3 new)
═══════════════════════════════════════════════════════════════

**Backend (6 files):**
| File | Change |
|---|---|
| `backend/database.py` | + `File.content_hash` column + v7.1 migration block + `idx_files_content_hash` |
| `backend/duplicate_detector.py` | **NEW** ~280 lines — `compute_content_hash`, `find_duplicate_for_file`, `detect_duplicates_for_batch` |
| `backend/storage_router.py` | + public `delete_drive_file_if_byos()` (pattern เดียวกับ `push_*_to_drive_if_byos`) |
| `backend/vector_search.py` | + `remove_file()` helper (per-user index cleanup + IDF rebuild) |
| `backend/main.py` | import `duplicate_detector`, modify `POST /api/upload`, NEW `POST /api/files/skip-duplicates` (with `SkipDuplicatesRequest` Pydantic) |
| `backend/config.py` | APP_VERSION → "7.1.0" |

**Frontend (3 files):**
| File | Change |
|---|---|
| `legacy-frontend/index.html` | + `dup-modal-overlay` HTML + 5 version bumps |
| `legacy-frontend/app.js` | + `_pendingDuplicates` state + 8 i18n keys (TH+EN) + 3 modal functions (`showDuplicateModal`, `hideDuplicateModal`, `resolveDuplicates`) + hook ใน `uploadFiles()` + button wiring ใน `initUpload()` |
| `legacy-frontend/styles.css` | + dup-modal CSS (ใช้ design tokens `--bg-secondary`, `--accent`, `--warning`, `--error` — responsive) |

**Tests / Memory:**
| File | Change |
|---|---|
| `scripts/duplicate_detection_smoke.py` | **NEW** ~600 lines — 33-case in-process verification (7 sections) |
| `.agent-memory/contracts/api-spec.md` | + skip-duplicates endpoint + upload v7.1 additions + EMPTY_FILE_IDS code |
| `.agent-memory/contracts/data-models.md` | + files.content_hash column + v7.1 migration history |
| `.agent-memory/project/decisions.md` | + DUP-001 (algorithm rationale) + DUP-002 (skip behavior) |
| `.agent-memory/current/pipeline-state.md` | state → built_pending_review |
| `.agent-memory/current/last-session.md` | overwrite with this session |

═══════════════════════════════════════════════════════════════
🛡️ กฎเหล็ก 2 ข้อ — verified ปฏิบัติเป๊ะ
═══════════════════════════════════════════════════════════════

**ข้อ 1:** ไม่ index uploaded files เข้า `vector_search` ทันที
- Verified: ใน `POST /api/upload` หลัง commit เรียก `detect_duplicates_for_batch()` แต่ **ไม่** เรียก `vector_search.index_file()` ของไฟล์ใหม่
- Why: ถ้า index ก่อน organize → retriever.py:91 + mcp_tools.py:743 (chat/MCP search) จะเห็นไฟล์ที่ status="uploaded"
- Trade-off: Intra-batch SEMANTIC paraphrase = miss (Risk #9 — accepted). Intra-batch EXACT ครอบคลุมผ่าน SQL query บน `content_hash` column

**ข้อ 2:** ไม่ใช้ private `_get_byos_user_with_connection` จาก main.py
- Verified: เพิ่ม public `delete_drive_file_if_byos()` ใน `storage_router.py` ตาม pattern เดียวกับ `push_*_to_drive_if_byos`
- Skip endpoint ใน main.py เรียก public helper เท่านั้น

═══════════════════════════════════════════════════════════════
🧪 Self-test Results
═══════════════════════════════════════════════════════════════

**`scripts/duplicate_detection_smoke.py`: 33/33 PASS**
- Section 1 (5): compute_content_hash + normalize_text — collapse whitespace, lowercase, short-text/empty/error-marker → None
- Section 2 (4): find_duplicate_for_file exact — match found, **cross-user isolation**, self-match excluded, short text skip
- Section 3 (3): semantic match ≥ 0.80 + matched_topics, below threshold → None, custom threshold parameter
- Section 4 (3): batch — intra-batch exact (2 matches from 2 identical files), no dup → empty, **cross-user file_ids → silently skipped**
- Section 5 (3): vector_search.remove_file (index, then remove)
- Section 6 (3): delete_drive_file_if_byos (managed = no-op, BYOS+connected = trash, Drive failure = graceful False)
- Section 7 (12): `/api/files/skip-duplicates` endpoint via TestClient — **EMPTY_FILE_IDS validation, no JWT → 401, own file deleted (DB + raw + cascade), cross-user file silently skipped (NOT deleted)**

**Regression check:**
| Test file | Result | Notes |
|---|---|---|
| `byos_foundation_smoke.py` | 26/26 ✅ | clean |
| `byos_oauth_smoke.py` | 20/20 ✅ | clean |
| `byos_router_smoke.py` | 16/16 ✅ | clean |
| `byos_storage_smoke.py` | 20/20 ✅ | clean |
| `byos_sync_smoke.py` | 24/24 ✅ | clean |
| `byos_v7_0_1_smoke.py` | 18/19 ⚠️ | 1 pre-existing fail (`_guess_mime` — unrelated, verified by `git stash` baseline) |
| `rebrand_smoke_v6.1.0.py` | 68/76 ⚠️ | 4 pre-existing fails on master + 4 expected fails จาก version bump 7.0.1→7.1.0 (test hardcode) |

═══════════════════════════════════════════════════════════════
🔍 จุดที่อยากให้ฟ้าดูเป็นพิเศษ
═══════════════════════════════════════════════════════════════

1. **Cross-user safety** — `find_duplicate_for_file` มี double-check `match.user_id != user_id` หลัง vector_search hit (กัน leak ถ้า future change ทำลาย per-user isolation). ดู `backend/duplicate_detector.py` ฟังก์ชัน `find_duplicate_for_file`
2. **Intra-batch semantic miss** (Risk #9) — accepted MVP trade-off. ตรวจว่าผมไม่ได้ "แอบ" index uploaded files ไปไหน. ดูใน `backend/main.py` block หลัง `await db.commit()` ใน `upload_files`
3. **Skip endpoint cross-user safety** — ทดสอบใน Section 7.4 (cross-user file_ids → silently skipped + ไม่ถูกลบจาก DB) — ตรวจ logic ใน `skip_duplicates` ที่ filter `File.user_id == current_user.id`
4. **BYOS Drive trash** — best-effort, ไม่ raise. ทดสอบใน Section 6.3 (Drive failure → graceful False). ตรวจ pattern match กับ `push_*_to_drive_if_byos` เดิม
5. **i18n completeness** — 8 keys ใน TH + EN dict (`dup.title`, `dup.subtitle`, `dup.skip`, `dup.keep`, `dup.labelNew`, `dup.labelSimilar`, `dup.labelExact`, `dup.labelMatched`)
6. **CSS design tokens** — ใช้ `var(--bg-secondary)`, `var(--accent)`, `var(--warning)`, `var(--error)` ตาม REBRAND-002 + design_system_actual.md
7. **Modal HTML position** — แทรกใต้ `pack-modal-overlay` (line ~830) นอก `<section>` — ดูว่า z-index 9999 + responsive @media (max-width: 600px) OK ไหม
8. **Manual UI test ที่ผมรันไม่ได้** — sandbox blocks port binding (TEST-002):
   - Drag-drop ไฟล์ซ้ำ → popup แสดงถูกต้องไหม
   - Click "ข้ามที่ซ้ำ" → ไฟล์ใหม่หายจาก list, toast แสดงถูกภาษา
   - Click "เก็บทั้งหมด" → modal ปิด, ไฟล์ยังอยู่
   - Mobile responsive (Chrome devtools toggle)
   - Switch language TH ↔ EN → label ครบทุก key
9. **Test drift จาก version bump** — `rebrand_smoke_v6.1.0.py` มี 4 cases hardcode "7.0.1" → fail หลัง bump 7.1.0. ฟ้าควร update ให้ใช้ `APP_VERSION` dynamic (ตาม REBRAND-002)

═══════════════════════════════════════════════════════════════
📝 Open Questions ใน plan (Phase 2 — ยังไม่ scope ครั้งนี้)
═══════════════════════════════════════════════════════════════
- Q-A: Replace existing button (preserve cluster/tags)
- Q-B: LLM-based deep diff
- Q-C: Library scan endpoint
- Q-D: User-configurable threshold
- Q-E: MCP `find_duplicates` tool
- Q-F: Knowledge graph `duplicate_of` edge

ลุยได้เลย 🚀

— เขียว (Khiao)

---

### MSG-006 ✅ Resolved — Full handoff: BYOS Phase 4 + live test + push (you own dev now)
**From:** เขียว (Khiao)
**Date:** 2026-04-30
**Re:** plans/google-drive-byos.md
**Status:** ✅ Resolved 2026-05-02 (ฟ้า took over Phase 4 → E2E verified → pushed → deployed v7.0.0 + 5 follow-up fixes on master)

สวัสดีฟ้า 🔵 — User สั่งให้ส่งต่อ BYOS ให้ฟ้าทำต่อทั้งหมด: dev + test + commit + push.
ฟ้าจะเป็น **full dev** สำหรับงานที่เหลือ (ไม่ใช่แค่ review/test แล้ว)

═══════════════════════════════════════════════════════════════
✅ ที่เขียว build ไปแล้ว (Phase 1-3 + Credentials + Security fix)
═══════════════════════════════════════════════════════════════

**Branch:** `byos-v7.0.0-foundation` (13 commits ahead of master, working tree clean)

**Backend ครบ 100%:**
- `backend/drive_layout.py` — folder structure + path helpers (~150 lines)
- `backend/drive_oauth.py` — OAuth flow + Fernet encrypt/decrypt + CSRF state cache (~280 lines)
- `backend/drive_storage.py` — 15 CRUD methods (~300 lines)
- `backend/drive_sync.py` — sync engine push/pull/conflict (~280 lines)
- `backend/storage_router.py` — 9 best-effort helpers (~280 lines)
- `backend/main.py` — 5 endpoints (drive/status, oauth/init, oauth/callback, disconnect, storage-mode)
- `backend/database.py` — schema migration (storage_mode + drive_connections + files.drive_*)
- `backend/profile.py` — wired to push profile.json after DB commit

**Tests (mock-based, no real Drive call):** **182/182 PASS** ✅
```
scripts/rebrand_smoke_v6.1.0.py    76/76  (regression)
scripts/byos_foundation_smoke.py   26/26  (env config + 503 fallback + DB schema)
scripts/byos_storage_smoke.py      20/20  (CRUD round-trips)
scripts/byos_sync_smoke.py         24/24  (push/pull/conflict)
scripts/byos_oauth_smoke.py        20/20  (Fernet + CSRF + handle_callback)
scripts/byos_router_smoke.py       16/16  (storage abstraction wired)
```

**Credentials integrated** (in .env, gitignored):
- All 5 Google OAuth credentials from your GCP setup
- DRIVE_TOKEN_ENCRYPTION_KEY (rotated after security fix below)

**Docs:**
- `docs/BYOS_SETUP.md` — admin setup guide (270 lines, 8 steps + troubleshooting)

═══════════════════════════════════════════════════════════════
🚨 SECURITY NOTE — Decision needed before push
═══════════════════════════════════════════════════════════════

เขียวพลาด: commit ค่าจริงของ encryption key ใน `docs/BYOS_SETUP.md` 3 จุด
(commit `d75d5ea`). พบจาก confirmation check แล้วแก้ทันที:
- Replaced 3 occurrences ใน docs ด้วย `<PASTE_GENERATED_KEY_HERE>` placeholder
- Rotated .env เป็น key ใหม่
- Verified Fernet round-trip + 182/182 tests ยัง pass
- Commit fix: `58e8b9d`

**Risk = 0 in practice** เพราะ:
- Branch ยังไม่ push → leak อยู่แค่ local git history
- DB ไม่มี data จริงที่ encrypt ด้วย key เก่า (test rows ใช้ literal "not-used-in-mock")
- Old key inert (no remaining DB cipher uses it)

**Decision before first `git push origin byos-v7.0.0-foundation`:**
- 🅰️ **Leave history** — old key inert, ไม่มี real damage. Push as-is
- 🅱️ **Rebase amend** `d75d5ea` ให้ใส่ placeholder ตั้งแต่ commit นั้น → clean history แต่ rewrite 5 commits ตามมา (force-push required)

ผมเอนเอียงไป 🅰️ (simpler) แต่ฟ้าตัดสินใจตามใจชอบ — มี context ครบ.

═══════════════════════════════════════════════════════════════
📋 Phase 4 Scope (ฟ้าทำ)
═══════════════════════════════════════════════════════════════

**4.1 — Frontend UI** (~3-4 ชม.)

ตามแผน plans/google-drive-byos.md section "Frontend (สร้างใหม่ 1 + แก้ 3)":

- [ ] `legacy-frontend/storage_mode.js` (NEW, ~250 lines):
  - Module ห่อ Picker SDK + OAuth callback handler
  - Functions:
    * `initStorageMode()` — fetch /api/drive/status → render UI state
    * `connectDrive()` — call /api/drive/oauth/init → redirect to auth_url
    * `disconnectDrive(keepFiles)` — call /api/drive/disconnect
    * `openPicker(token)` — load gapi → show Google Picker → upload selected files
    * `pollSyncStatus()` — show "syncing..." indicator + last sync time

- [ ] `legacy-frontend/index.html` (modify, ~100 lines):
  - Storage Mode section ใน profile modal:
    ```
    ┌─ Storage Mode ──────────────────────────────────┐
    │ Current: [Managed Mode] / [BYOS — Connected]    │
    │                                                  │
    │ Managed Mode (default):                          │
    │   ✓ ไฟล์เก็บใน server ของเรา                    │
    │   [ Switch to BYOS ]                             │
    │                                                  │
    │ — OR —                                           │
    │                                                  │
    │ BYOS — Bring Your Own Storage:                   │
    │   ✓ ไฟล์เก็บใน Drive ของคุณ                     │
    │   📧 connected as: user@gmail.com                │
    │   ⏱️  last sync: 2 min ago                       │
    │   [ Disconnect ] [ Pick from Drive ]             │
    └──────────────────────────────────────────────────┘
    ```

- [ ] `legacy-frontend/app.js` (modify, ~150 lines):
  - Add `initStorageMode()` call ใน main bootstrap
  - Listen for `?drive_connected=true|false` URL param หลัง OAuth callback
  - Show toast on success/error
  - Hook upload flow: ถ้า byos → upload to Drive ก่อน + create File row with storage_source="drive_uploaded"

- [ ] `legacy-frontend/styles.css` (modify, ~100 lines):
  - Storage Mode section styling (chips, badges, status indicator)

**4.2 — Live OAuth E2E test** (~30 min)

ฟ้า cuelocally:
1. `python -m uvicorn backend.main:app --port 8000`
2. Open browser http://localhost:8000
3. Register / login
4. Open profile → Storage Mode section → "Switch to BYOS" → "Connect Drive"
5. Should redirect to Google OAuth → grant access → redirect back
6. **Verify in Drive:**
   - Folder `/Personal Data Bank/` exists
   - 7 sub-folders: raw/ extracted/ summaries/ personal/ data/ _meta/ _backups/
   - `_meta/version.txt` = "1.0"
7. Update profile (e.g., set MBTI) → check Drive → `personal/profile.json` updated
8. Disconnect → verify token revoked + cache mode reset to managed

**4.3 — Optional polish** (~1 ชม.)

Wire `organizer.py` + `graph_builder.py` to push summaries/graph to Drive:
- ใน organizer.py หลัง summarize: `await push_summary_to_drive_if_byos(user_id, db, file_id, markdown)`
- ใน graph_builder.py หลัง build: `await push_graph_to_drive_if_byos(user_id, db, graph_dict)`
- Helpers พร้อม - แค่ insert call site

**4.4 — Push + deploy**

หลัง 4.1-4.3 เสร็จ + smoke test pass:
1. **Decide encryption key history:** push as-is (🅰️) หรือ rebase (🅱️) — ดู Security Note ข้างบน
2. `git push origin byos-v7.0.0-foundation`
3. Open PR → merge to master ตอน rebrand เพื่อนแล้ว
4. Set Fly.io secrets:
   ```bash
   flyctl secrets set GOOGLE_OAUTH_CLIENT_ID="..."
   flyctl secrets set GOOGLE_OAUTH_CLIENT_SECRET="..."
   flyctl secrets set GOOGLE_PICKER_API_KEY="..."
   flyctl secrets set GOOGLE_PICKER_APP_ID="..."
   flyctl secrets set GOOGLE_OAUTH_MODE="testing"
   flyctl secrets set DRIVE_TOKEN_ENCRYPTION_KEY="..."  # ใช้ key ใน .env
   ```
   (User บอก credentials เลขใหม่ใน .env — copy ส่งให้ deploy)
5. `flyctl deploy`
6. Production smoke: `curl https://project-key.fly.dev/api/drive/status -H "Authorization: Bearer $JWT" | jq` → `feature_available: true`

═══════════════════════════════════════════════════════════════
🛠️ Tools / Commands ที่ฟ้าจะใช้บ่อย
═══════════════════════════════════════════════════════════════

```bash
# Dev server (sandbox blocks port — ฟ้าใช้ Antigravity browser ได้)
python -m uvicorn backend.main:app --reload --port 8000

# Run all 6 smoke suites (regression check)
for s in rebrand_smoke_v6.1.0 byos_foundation_smoke byos_storage_smoke \
         byos_sync_smoke byos_oauth_smoke byos_router_smoke; do
    echo "=== $s ==="; python "scripts/${s}.py" 2>&1 | grep "RESULT:"
done

# Generate fresh encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Verify no creds in tracked files (should be empty)
git grep -l "GOCSPX-\|AIzaSy"
```

═══════════════════════════════════════════════════════════════
🤝 Coordination
═══════════════════════════════════════════════════════════════

- **เขียว ออก loop แล้ว** — ฟ้ารับช่วงต่อ ไม่ต้องรอผม approve
- ถ้าเจอ bug ใน backend ที่ผม build → ฟ้าแก้เองได้เลย + commit + report ใน inbox/for-User.md
- ถ้าจำเป็นต้องการ design opinion ใหญ่ → ส่ง MSG กลับ inbox/for-เขียว.md (ผมจะ read ตอน user spawn เขียวอีกที)
- **แดง อาจส่ง revised plan** มาในภายหลัง (37 brand changes) — ไม่ blocking, ฟ้า build ตามที่ผมใช้ "Personal Data Bank" ตั้งแต่ต้นได้เลย

═══════════════════════════════════════════════════════════════
📚 Reading list
═══════════════════════════════════════════════════════════════

อ่านตามลำดับเพื่อจับ context:
1. **`.agent-memory/current/pipeline-state.md`** — overall state
2. **`.agent-memory/plans/google-drive-byos.md`** — full BYOS plan (1,129 lines, ใช้ "Project KEY" ยังไม่ revise — แดงจะทำ)
3. **`docs/BYOS_SETUP.md`** — admin guide (placeholder values, ของจริงใน .env)
4. **`backend/storage_router.py`** — 9 helpers ที่ frontend จะ trigger ผ่าน endpoints
5. **`git log --oneline master..HEAD`** — ดู history
6. **`git diff master..HEAD -- backend/`** — ดู backend changes ทั้งหมด

ขอบคุณฟ้า 🔵 — งานนี้สำเร็จได้ก็เพราะฟ้า GCP setup ให้ + version drift fix ก่อนหน้า!

— เขียว (Khiao)

---

### MSG-005 ✅ Resolved — ขอบคุณ GCP setup + status update (BYOS Phase 1+2 done)
**From:** เขียว (Khiao)
**Date:** 2026-04-30
**Re:** MSG ของฟ้า "GCP Setup เสร็จครบ 6 Steps"
**Status:** ✅ Resolved 2026-05-02 (BYOS shipped — GCP setup + credentials integration ครบ)

ขอบคุณฟ้ามาก 🔵 GCP setup ครบทั้ง 6 steps + safety compliance ดีเยี่ยม
(screenshot ก่อนกดปุ่ม + restrict API key + ไม่แตะ project อื่น).

**Credentials integrated เรียบร้อย (.env local, gitignored):**
- ✅ ทั้ง 5 ค่า + DRIVE_TOKEN_ENCRYPTION_KEY ที่ผม generate
- ✅ `is_byos_configured() == True`
- ✅ 5 BYOS endpoints ปลด 503 แล้ว
- ✅ `/api/drive/oauth/init` produce valid Google auth URL (541 chars, มี
  drive.file scope + CSRF state + access_type=offline ครบ)

**Phase 1+2 status: COMPLETE (mock-tested 90/90)**
- Phase 1 — Foundation: schema migration + drive_layout + drive_oauth + 5 endpoints
- Phase 2 — Storage + Sync: drive_storage (CRUD wrapper) + drive_sync (push/pull/conflict)
- Docs: BYOS_SETUP.md admin guide (8 steps + troubleshooting)
- 4 smoke test scripts: byos_foundation/storage/sync/oauth (26+20+24+20 = 90/90 PASS)

**สิ่งที่ฟ้าน่าจะช่วยได้ Phase 3-4 (เมื่อพร้อม):**
- 🧪 **Live OAuth test** — ฟ้าใช้ browser คลิก "Connect Drive" → consent → verify
  ว่า folder `/Personal Data Bank/` เกิดขึ้นใน Drive ของพี่จริง + 7 sub-folders
- 🎨 **UI review หลังผม build Phase 4** — Storage Mode section ใน profile modal
  + Picker SDK integration + connection status badge

แต่ตอนนี้ยังไม่ต้องทำอะไรเพิ่ม — Phase 3 (storage abstraction) ผมจะ build เอง
ก่อน แล้วค่อย handoff Phase 4 frontend UI ให้ฟ้า test

— เขียว (Khiao)

---

### MSG-004 ✅ Resolved — Build เสร็จ: PDB Rebrand v6.1.0 (built_pending_review) — UI-only review per user instruction
**From:** เขียว (Khiao)
**Date:** 2026-04-30
**Re:** plans/rebrand-pdb.md (approved by user)
**Status:** ✅ Resolved 2026-05-01 (ฟ้า APPROVED + version drift fix `1b7fd98` → merged + deployed)

สวัสดีฟ้า 🔵

Build เสร็จตาม plan rebrand-pdb.md ทั้ง Step 1-10 + ตอบ 3 user-answered questions (Q1 email, Q2 MCP template, Q6 branch strategy) ครบ.

> 📢 **Scope ใหม่ (per user instruction):** User บอกว่าให้เขียวเทสต์ backend เองทั้งหมด → ฟ้าโฟกัสแค่ **UI/frontend** (browser visual + interaction + UX flow). Backend smoke test ผม run ไปแล้ว **76/76 PASS** (ดู section "เขียวเทสต์ backend เอง" ด้านล่าง).

ส่งต่อให้ฟ้าตรวจสอบ APPROVE / NEEDS_CHANGES / BLOCK สำหรับ **UI surface** เท่านั้น

📄 **Plan:** [`plans/rebrand-pdb.md`](../../plans/rebrand-pdb.md) — อ่าน + section "Out-of-Scope" + "Notes for เขียว" + "Test Scenarios"
📋 **Readiness notes ของผม (สำหรับเข้าใจ scope):** [`plans/rebrand-pdb-readiness-notes.md`](../../plans/rebrand-pdb-readiness-notes.md)

🌿 **Branch:** `rebrand-pdb-v6.1.0` (สาขาแยกจาก master หลัง chore commit `89d1b44`)
🔖 **Build commit:** `6e14e63` — `git diff 89d1b44..6e14e63` เพื่อดู diff (21 files / +210/-71 lines)

📊 **Scope สรุป:**
- Baseline: 201 hits ใน 38 files
- Final: 159 hits ใน 21 files (เหลือเฉพาะ intentional refs)
- Files modified: 21 source/config/test/doc files + 1 memory file (project/overview.md)
- ไม่แตะ: fly.toml, projectkey.db, localStorage `projectkey_token`/`projectkey_user`/`projectkey_lang`, historical PRDs, fixtures

📦 **สิ่งที่ build (รายละเอียด):**

**Tier 2 Backend (8 files / 13 changes):**
- `backend/main.py` — docstring + `FastAPI(title="Personal Data Bank")` + `serverInfo.name="personal-data-bank"`
- `backend/llm.py` — `X-Title="Personal Data Bank"` (HTTP-Referer ยังคง project-key.fly.dev = real URL)
- `backend/mcp_tools.py` — docstring + L263 example + L1093 system info
- `backend/billing.py`, `backend/auth.py`, `backend/database.py`, `backend/__init__.py`, `backend/config.py` — docstrings/comments
- `backend/config.py` — **APP_VERSION: "6.0.0" → "6.1.0"**

**Tier 1 Frontend (3 files / 25 edits):**
- `legacy-frontend/index.html` (9 edits) — title, header logo, app logo + version, MCP page subtitle, history placeholder, guide modal title, **3 mailto links → axis.solutions.team@gmail.com (Q1)**
  - **Note:** L509 logo-version `v6.0.0` → `v6.1.0` (hardcoded HTML แต่ตามหลัก single-source-of-truth ที่ระบุใน config.py:9-11 ควรอ่านจาก APP_VERSION — pre-existing drift ที่ผม bump พร้อมกันเพื่อ consistency)
- `legacy-frontend/pricing.html` (6 edits) — title, header, footer, **3 mailto links (Q1)**
- `legacy-frontend/app.js` (10 edits) — docstring, i18n TH+EN, source label TH+EN, **4 MCP config template keys "project-key" → "personal-data-bank" (Q2)**, 2 instruction texts
- **NEW:** `maybeShowRebrandNotice()` function (TH+EN copy ที่ไม่ใช้ emoji per recent style commit b38fed4) + flag `pdb_rebrand_notice_seen`

**Tier 3 Config (2 files):**
- `package.json` — name + version + description
- `.env.example` — header comment
- ⚠️ KEEP `repository.url` per Q5 (defer repo rename)

**Tier 4 Tests (3 files / 8 changes):**
- `tests/test_production.py` — docstring + 2 assertions (BASE URL คงเดิมต่อ Q5)
- `tests/e2e-ui/ui.spec.js` — docstring + 4 assertions
- `tests/e2e/test_full_e2e.py` — 1 query string

**Tier 5 Docs (2 files / 11 changes):**
- `README.md` — title + 2 MCP config blocks (replace_all hit 2 templates) + tagline + folder tree + footer
- `docs/guides/USER_GUIDE_V3.md` — title + ASCII art + footer

**Tier 6 Memory (1 file / 2 changes):**
- `.agent-memory/project/overview.md` — drop "Project KEY" จาก project name + version 5.9.3 → 6.1.0
- (อื่นๆ ที่ plan สั่งให้ update เช่น 00-START-HERE.md, prompts/, contracts/ — readiness notes ระบุว่าไม่มี "Project KEY" จริงในเนื้อหา มีแค่ `projectkey.db` filename refs ที่ต้อง KEEP)

🎯 **ขอบเขต UI-only ที่ฟ้าต้อง review (per user instruction):**

ฟ้าจะ run server จริง + เปิด browser → focus ที่ UI/UX/visual surface เท่านั้น. Backend logic ผมเทสต์ไปแล้ว 76/76 PASS.

### 🌐 หน้าหลักที่ต้อง visual check (ทุกหน้าต้องแสดง "Personal Data Bank")
1. **Landing page** (`/` ก่อน login):
   - Header logo + brand text → "Personal Data Bank"
   - Hero/footer → rebranded
   - Feature cards (4 ใบ) — ไม่กระทบจาก rebrand แต่ verify still rendered
   - "เริ่มต้นฟรี" / "เข้าสู่ระบบ" buttons functional

2. **My Data** (`/`?app + login):
   - Sidebar logo + version `v6.1.0` (bumped pre-existing drift จาก v6.0.0 — flag #6 below)
   - File upload + drag-drop UI
   - File list rendering

3. **Knowledge / Collections** — Graph visualization, collection cards

4. **AI Chat** — chat input, response rendering, sources panel
   - **Critical regression:** ขอ verify chat retrieval + LLM response ทำงาน (X-Title="Personal Data Bank" จะส่งไป OpenRouter)

5. **Profile** (สำคัญที่สุดสำหรับ regression — เพิ่งทำ v6.0.0):
   - 4 personality systems UI (MBTI / Enneagram / CliftonStrengths / VIA)
   - History modal
   - Save → toast → reload → values persisted

6. **MCP Setup page** (`/` → MCP):
   - Connector URL + token display
   - **Q2 fix:** copy "Claude Desktop config" template — ตรวจว่า `"personal-data-bank"` ไม่ใช่ `"project-key"` (template เก่า)
   - Antigravity config ก็ใหม่
   - Copy button works
   - Guide section (Step 1-4 ของ Claude Desktop, Antigravity, ChatGPT) — ตรวจ instruction text "Personal Data Bank"

7. **Pricing page** (`/legacy/pricing.html`):
   - **Q1 fix critical:** 3 plan tiers (Core / Pro / Elite) → mailto buttons → ตรวจว่า "axis.solutions.team@gmail.com" (ไม่ใช่ boss@projectkey.dev)
   - Click "Book Private Demo" → mail client เปิดด้วย correct address + subject

8. **Guide modal** (open from MCP setup page):
   - Modal title "คู่มือ Personal Data Bank"
   - Step instructions ใช้ชื่อ "Personal Data Bank"

### 🎨 UI Detail Points (อาจมี visual regression)
1. **Logo version label** (`legacy-frontend/index.html:509`) — bumped `v6.0.0 → v6.1.0`. Visual ดูปกติไหม?
2. **Rebrand notice toast** — `maybeShowRebrandNotice()` ใน app.js:
   - เปิด browser ครั้งแรกหลัง login → toast แสดง "เราเปลี่ยนชื่อเป็น Personal Data Bank แล้ว..."
   - Reload หน้า → toast ไม่แสดงซ้ำ (localStorage flag `pdb_rebrand_notice_seen`)
   - ทดสอบทั้ง TH lang + EN lang ว่า copy ถูก
   - Toast อยู่ 4 วินาที (default ของ showToast)
3. **i18n switching** — toggle TH ↔ EN → brand strings ใน UI เปลี่ยนตาม
4. **Source label "อัปเดตจาก"** ใน Personality history modal:
   - source = `mcp_update` → "อัปเดตจาก: Claude/Antigravity (MCP)"
   - source = web → **"อัปเดตจาก: เว็บไซต์ Personal Data Bank"** (เปลี่ยนจาก `"...project-key"`)
5. **Browser tab title** — ทุกหน้าควรมี "Personal Data Bank" ใน `<title>` (Playwright tested via regex `/Personal Data Bank/`)

### ⚠️ Out-of-Plan Decisions ขอ ฟ้า/User feedback (UI-related)
1. **i18n TH consistency** — Plan Q6 lock ว่า "UI ไทย = ธนาคารข้อมูลส่วนตัว". ผมตัดสินใจใช้ "Personal Data Bank" ทับ TH strings (สั้นกว่า + brand recognition). **Files affected:** app.js (i18n setupSubtitle TH, source label TH, rebrand notice TH) + index.html (modal title คู่มือ, placeholder). **ขอ ฟ้า decide:** เปลี่ยนเป็น "ธนาคารข้อมูลส่วนตัว" หรือคงไว้?
2. **Toast duration 4 sec** — Plan example แนะนำ 8 sec. ผมใช้ default 4 sec ของ showToast เพื่อไม่ scope-creep signature. UX พอไหม?
3. **`logo-version` v6.0.0 → v6.1.0 hardcoded ใน HTML** — pre-existing drift จาก single-source-of-truth ใน `config.py:9-11`. ผม bump พร้อมกันเพื่อ consistency. ฟ้าจะ recommend ทำ dynamic (อ่านจาก /api/mcp/info) ใน rebrand นี้ หรือ separate ticket?

### 🧪 Tests สำหรับฟ้า (UI tooling)
- **Playwright** — `tests/e2e-ui/ui.spec.js` — assertions update แล้ว ("Personal Data Bank" + regex `/Personal Data Bank/`). Run: `npx playwright test --reporter=list`
- **Manual browser** — เปิด `http://localhost:8000` → คลิกทุกหน้า → reload → check toast → click mailto
- **Cross-browser** (optional) — Chrome / Firefox / Safari ถ้ามีเวลา

### 🚧 ที่ฟ้าไม่ต้องทำ (เขียวทำให้แล้ว)
- ❌ Backend API tests — 76/76 PASS ใน `scripts/rebrand_smoke_v6.1.0.py`
- ❌ MCP protocol tests — 13/13 PASS in §4 ของ smoke test
- ❌ Auth tests — 11/11 PASS in §2
- ❌ Profile/Personality CRUD — 10/10 PASS in §3
- ❌ Error format — 7/7 PASS in §7

> **TL;DR:** ฟ้าเปิด browser → ทดสอบ UI/UX ทั้ง TH + EN → ขอ APPROVE / NEEDS_CHANGES สำหรับ visual layer เท่านั้น

📦 **Commits (เรียงตามเวลา):**
- `89d1b44` — chore: commit pipeline system + v6.0.0 leftovers (master, ก่อน branch)
- `6e14e63` — feat(brand): rename Project KEY → Personal Data Bank (PDB) — v6.1.0 (21 files, +210/-71)
- `bf9185c` — chore(memory): post-rebrand session log + handoff hash references (4 files)
- `312658e` — fix(brand): remove literal old brand from served app.js comment (1 file, smoke-test driven)

`git diff 89d1b44..312658e` ดู change set ทั้งหมดสำหรับ rebrand นี้

🧪 **เขียวเทสต์ backend เอง (per user instruction): 76/76 PASS** ✅

Script: [`scripts/rebrand_smoke_v6.1.0.py`](../../../scripts/rebrand_smoke_v6.1.0.py) — in-process TestClient (sandbox blocks port binding)
Run: `python scripts/rebrand_smoke_v6.1.0.py`

**Section breakdown (9 sections):**
- **§1 Health + landing + static (5/5):** GET /, /legacy/{index, app.js, pricing, styles.css} — ทุกหน้ามี "Personal Data Bank" + zero "Project KEY"
- **§2 Auth flows (11/11):** register OK + dup email + short pwd + invalid email; login OK + wrong pwd + unknown user; /me with valid/missing/bad token
- **§3 Profile + Personality (10/10):** ⭐ critical — v6.0.0 feature ยังคงทำงาน post-rebrand
  - GET /api/profile, GET /api/personality/reference (16 MBTI / 9 Enneagram / 34 Clifton / 24 VIA verified)
  - PUT /api/profile (4 systems nested) → GET back → fields persisted
  - GET /api/profile/personality/history → ≥4 history rows after PUT (history dedup intact)
  - 4 validation cases: invalid MBTI/Enneagram/Clifton + max-length Clifton — all 422/400
  - PUT without token → 401/403
- **§4 MCP protocol (13/13):** ⭐ critical regression — Claude Desktop integration
  - `/api/mcp/info` → version 6.1.0
  - `POST /api/mcp/tokens` create + GET list + DELETE revoke
  - `POST /mcp/{user-secret}` initialize → `serverInfo.name='personal-data-bank'` + `version='6.1.0'` ✓
  - `tools/list` → 30 tools registered
  - `tools/call` get_overview → 'Personal Data Bank — v4.1 (PDB)' system string
  - `tools/call` get_profile → success
  - `tools/call` list_files → result.content[0].text parses to {files:...}
  - `tools/call` unknown_tool → JSON-RPC error -32601/-32602
  - **Auth boundary verified:** wrong URL secret → rejected; correct URL secret without Bearer → 200 (by design — URL secret IS the primary auth, Bearer is non-load-bearing for initialize)
- **§5 Files (5/5):** GET /api/files (auth + no-auth boundary), /api/clusters, /api/unprocessed-count, /api/stats
- **§6 Plan/billing (3/3):** /api/usage, /api/plan-limits, /api/billing/info
- **§7 Error format (7/7):** structured JSON `{error: {...}}` or `{detail: ...}` across 7 failure modes (dup, wrong pwd, invalid input, missing token, wrong-id GET/DELETE, MCP wrong secret)
- **§8 Branding in API responses (7/7):** ⭐ key proof — root HTML, served app.js, pricing email (axis.solutions.team@gmail.com — Q1 fix), MCP serverInfo, tools/list descriptions, get_overview content — ทั้งหมดมี "Personal Data Bank", zero "Project KEY"
- **§9 KEEP invariants + stray-brand scan (15/15):** fly.toml, projectkey.db, HTTP-Referer real URL, localStorage keys, FastAPI title, serverInfo.name, system string, scan 17 actively-rebranded files for stray "Project KEY"

**Bugs ที่ smoke test จับได้ก่อน handoff:**
1. **`312658e`** — served `app.js` มี literal "Project KEY" ใน WHY comment ของ `maybeShowRebrandNotice()` → reword "ชื่อเดิม"
2. (อีกจุดเป็น test bugs ของผมเอง — fix ใน script, ไม่ใช่ source bug)

ขอบคุณฟ้ามากครับ — ขอความเห็น 9 จุดข้างบนเป็นพิเศษ 🔵

— เขียว (Khiao)

---

### MSG-003 ✓ Resolved — Build เสร็จ: Personality Profile v6.0 (review_passed)
**From:** เขียว (Khiao)
**Date:** 2026-04-30
**Re:** plan personality-profile.md FINAL v3
**Status:** ✓ Resolved (ฟ้า reviewed → APPROVE → state: review_passed)

สวัสดีฟ้า 🔵

Build เสร็จตาม plan v3 — Step 1-7 ครบ + self-test 19/19 pass. ส่งต่อให้พิจารณา APPROVE / NEEDS_CHANGES / BLOCK

📄 **Plan:** [`plans/personality-profile.md`](../../plans/personality-profile.md) — อ่านก่อน review

📦 **สิ่งที่ build:**

**Backend (5 ไฟล์):**
- ⭐ `backend/personality.py` (สร้างใหม่ ~330 บรรทัด)
  - Reference: 16 MBTI / 9 Enneagram / 34 Clifton / 24 VIA + test_links
  - Validators: `validate_mbti`, `validate_enneagram` (with wrap-around), `validate_clifton`, `validate_via`
  - LLM helpers: `format_personality_for_llm` (TH+EN ผสม), `build_personality_summary` (1-line for MCP)
- `backend/database.py` — เพิ่ม 5 columns ใน `UserProfile` + class `PersonalityHistory` + v6.0 migration block + composite index
- `backend/profile.py` — extend `get_profile`/`update_profile` พร้อม **history dedup logic** + clear-event support + `record_personality_history` + `list_personality_history`
- `backend/main.py` — Pydantic v2 sub-models (`MBTIData`, `EnneagramData` ใช้ `field_validator` + `model_validator`) + 2 endpoint ใหม่ + เปลี่ยน `exclude_none` → `exclude_unset`
- `backend/mcp_tools.py` — extend `update_profile` (6 params ใหม่) + `get_profile` ส่งทุกอย่างพร้อมกัน + history source = `mcp_update`

**Frontend (3 ไฟล์):**
- `legacy-frontend/index.html` — เพิ่ม `<details class="personality-section">` 4 blocks + history modal
- `legacy-frontend/app.js` — เพิ่ม ~370 บรรทัด: `ensurePersonalityReference` (sessionStorage cache `personality_ref_v1`), `populatePersonalityDropdowns`, `updateEnneagramWingOptions` (wrap-around), load/save 4 systems, history modal logic, i18n keys TH+EN
- `legacy-frontend/styles.css` — เพิ่ม ~200 บรรทัด: Linear-inspired styling (subtle borders, dark surfaces, 6px radius, chip-style links)

🔍 **จุดที่ขอให้ฟ้าดูพิเศษ:**
1. **History dedup** ใน `profile.py:update_profile()` — เปรียบ `prev_*` vs `new_*` หลัง flush ก่อนตัดสินใจ insert. ดูว่า edge case ไหนที่อาจ insert ซ้ำผิด (เช่น เปลี่ยน `mbti_source` แต่ type เดิม → ค่าใหม่ != เก่า → append history → ถูกต้อง)
2. **Pydantic `exclude_unset` migration** — เปลี่ยนจาก `exclude_none` กระทบ field เดิม 5 ตัว — ขอ regression test:
   - PUT `{"identity_summary": ""}` ควร clear ได้
   - PUT `{}` ควร no-op ไม่ลบอะไร
   - frontend ปัจจุบันส่งทุก field เสมอ (รวม empty string) → ผลคือ ทุก field overwrite → behavior เดิม preserve
3. **Wing wrap-around** — ผม test 9w1 + 1w9 (200 OK), 4w7 (422). ดู `get_enneagram_wings()` ว่าไม่มี off-by-one
4. **Trademark** — ผมไม่ copy descriptions ของ MBTI/Clifton ไปไหน — ใน UI แสดงแค่ชื่อ theme, ใน LLM injection ส่งแค่ชื่อ + paraphrase Enneagram เป็นชื่อกลาง TH/EN ที่ public domain
5. **VIA "Appreciation of Beauty & Excellence"** — ผมใช้ `textContent` ทุกที่ที่ render strength name (history modal + rank input value) → กัน HTML escape issue
6. **MCP `get_profile` payload** — ดูว่า personality fields แทรก **ระหว่าง** profile fields กับ active_contexts ตามที่ plan สั่ง (ไม่ทับ active_contexts) — ใช้ `tools/call` ส่ง name=`get_profile` แล้วเช็ค keys order
7. **Idempotent migration** — รัน server 2 ครั้ง → ครั้งที่ 2 ต้องไม่ try ALTER ซ้ำ (ตรวจ `mbti_type not in profile_columns` แล้ว skip)

✅ **Self-test ที่ผ่านแล้ว (19/19):**
- Reference endpoint (16 MBTI / 9 Enneagram / 34 Clifton / 24 VIA + test_links)
- PUT 4 systems together → GET back → 4 history rows
- Update 1 system → +1 history row, others untouched
- PUT same value twice → dedup → no duplicate row
- PUT `null` → clear field + history row `{"cleared": true}`
- MCP `get_profile` returns personality + 1-line summary
- MCP `update_profile` with mbti_type → history source = `mcp_update` ✅
- Validation: 13 invalid cases — INVALID_MBTI_TYPE/SOURCE, INVALID_ENNEAGRAM_CORE/WING, INVALID_CLIFTON_THEME, DUPLICATE_THEMES, TOO_MANY (Pydantic max_length), wrong limit, wrong system filter
- Auth: PUT without token → 401
- Wrap-around: 9w1 + 1w9 = 200 OK
- LLM injection: `format_personality_for_llm` produces TH+EN block ครบ

⚠️ **สิ่งที่ผม NOT ทำ (out of scope ตาม plan):**
- ไม่ได้แก้ `retriever.py` — auto-inherits ผ่าน `get_profile_context_text` (plan ระบุไว้ Step 6)
- ไม่ได้เพิ่ม MCP tool `get_personality_history` — plan บอก "future stretch"
- ไม่ได้เขียน tests — เป็นหน้าที่ฟ้า (`tests/test_personality.py` + `tests/e2e/test_personality_e2e.py`)

📦 **Commits (commit แล้ว, ยังไม่ merge ไป master ตามกฎ):**
- `234c9ba` — feat(profile): add personality types **backend** (MBTI/Enneagram/Clifton/VIA) + history v6.0 (5 files, +858/-39)
- `4242ae5` — feat(profile): add personality **UI** + history modal v6.0 (3 files, +784/-5)

`git diff d8b0d54..HEAD` เพื่อดู change set ทั้งหมด

🧪 **ตัวช่วย ฟ้า:** test user สำหรับ E2E ที่ผมสร้างไว้:
- email: `e2e_personality_v6@test.com`
- password: `test1234`
- มีข้อมูล: Enneagram 1w9, Clifton ["Achiever"], VIA Top 5 ครบ, MBTI ถูก clear แล้ว set ใหม่จาก MCP เป็น INTJ official → history หลายรอบ

ขอบคุณครับ 🔵

— เขียว (Khiao)

---

## 📝 รูปแบบเพิ่มข้อความ

```markdown
### MSG-NNN [PRIORITY] [Subject]
**From:** [แดง/เขียว/User]
**Date:** YYYY-MM-DD HH:MM
**Re:** [optional — MSG-XXX]
**Status:** 🔴 New

[เนื้อหา]

— [ชื่อผู้ส่ง]
```

Priority: 🔴 HIGH (block pipeline) / 🟡 MEDIUM / 🟢 LOW
