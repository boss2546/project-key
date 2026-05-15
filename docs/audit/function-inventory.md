# 📋 PDB Function Inventory — Checklist

> **เวอร์ชัน:** v9.4.9 · **อัปเดต:** 2026-05-14
> **รวม:** 819 functions · 69 classes ใน 50 files (43 Python + 7 JS)
> **วัตถุประสงค์:** ใช้ติ๊กรายฟังก์ชัน — ฟังก์ชันไหนเข้าใจแล้ว / ตรวจแล้ว / refactor ได้ปลอดภัย / ลบทิ้งได้

## วิธีใช้ checklist
- `- [ ]` = ยังไม่ตรวจ
- `- [x]` = ตรวจแล้ว/เข้าใจแล้ว
- ขีดฆ่า (`~~func~~`) = ตกลงว่าจะลบ
- ⚠️ = ฟังก์ชันใหญ่/อันตราย/touchpoint หลัก
- 🟡 = disabled/deprecated อยู่
- 🔥 = hotspot (ถูกเรียกบ่อย/เป็นจุดเริ่มของ flow)

---

# 📑 สารบัญ

1. [🔐 Auth + Login](#1--auth--login)
2. [📤 Upload + Queue](#2--upload--queue)
3. [📄 Extraction + AI Ingest](#3--extraction--ai-ingest)
4. [🗃️ Files + Organize](#4--files--organize)
5. [🧠 Knowledge Graph + Search](#5--knowledge-graph--search)
6. [📦 Context Packs + Share](#6--context-packs--share)
7. [💾 Storage Router (Local/Drive)](#7--storage-router-localdrive)
8. [💬 LINE Bot](#8--line-bot)
9. [🤖 MCP Server](#9--mcp-server)
10. [👤 Profile + Personality + Context Memory](#10--profile--personality--context-memory)
11. [💳 Billing + Plan Limits](#11--billing--plan-limits)
12. [🛠️ Admin + Misc + Infra](#12-️-admin--misc--infra)
13. [📚 Frontend ที่ยังไม่แบ่งกลุ่ม](#13--frontend-misc)

---

# 1. 🔐 Auth + Login

> **บทบาท:** สมัครสมาชิก · ล็อกอิน · รีเซ็ตรหัส · Google Sign-In · ออก token JWT
> **ฟังก์ชัน:** 32 · **อันตราย:** 🔥 race condition เพิ่ง fix ใน v9.4.9

## 1.1 [backend/auth.py](../../backend/auth.py) — JWT + password core

- [ ] `hash_password` ([auth.py:25](../../backend/auth.py#L25)) — bcrypt hash รหัสผ่าน
- [ ] `verify_password` ([auth.py:30](../../backend/auth.py#L30)) — เช็ค hash กับ plaintext
- [ ] `create_access_token` ([auth.py:35](../../backend/auth.py#L35)) — ออก JWT (ใช้ตอน login สำเร็จ)
- [ ] `decode_token` ([auth.py:48](../../backend/auth.py#L48)) — verify+decode JWT
- [ ] `register_user` ([auth.py:57](../../backend/auth.py#L57)) — สมัครใหม่ + free plan
- [ ] `login_user` ([auth.py:111](../../backend/auth.py#L111)) — login ด้วย email/password
- [ ] `get_current_user` ([auth.py:165](../../backend/auth.py#L165)) ⚠️ — DI dependency ตัวหลัก (ทุก endpoint ที่ต้อง auth ใช้อันนี้)
- [ ] `require_admin` ([auth.py:207](../../backend/auth.py#L207)) — เช็ค is_admin=True
- [ ] `get_optional_user` ([auth.py:240](../../backend/auth.py#L240)) — auth optional (สำหรับ public endpoints)
- [ ] `create_reset_token` ([auth.py:272](../../backend/auth.py#L272)) — token สำหรับรีเซ็ตรหัส
- [ ] `decode_reset_token` ([auth.py:285](../../backend/auth.py#L285))
- [ ] `request_password_reset` ([auth.py:296](../../backend/auth.py#L296)) — สร้าง token + ส่งเมล
- [ ] `reset_password` ([auth.py:337](../../backend/auth.py#L337)) — verify token + เปลี่ยนรหัส
- [ ] `login_or_create_google_user` ([auth.py:389](../../backend/auth.py#L389)) ⚠️ — Google login → upsert user

## 1.2 [backend/google_login.py](../../backend/google_login.py) — Google OAuth flow

- [ ] `_cleanup_expired_states` ([google_login.py:72](../../backend/google_login.py#L72)) — clear state cache
- [ ] `_build_login_flow` ([google_login.py:83](../../backend/google_login.py#L83)) — build OAuth flow object
- [ ] `init_google_login` ([google_login.py:108](../../backend/google_login.py#L108)) — สร้าง authorize URL
- [ ] `_verify_id_token` ([google_login.py:153](../../backend/google_login.py#L153)) — verify Google ID token signature
- [ ] `handle_google_callback` ([google_login.py:188](../../backend/google_login.py#L188)) ⚠️ — callback handler ตัวหลัก
- [ ] `_reset_state_cache_for_testing` ([google_login.py:242](../../backend/google_login.py#L242))
- [ ] **class** `_StateEntry`, `_GLoginResult`

## 1.3 [backend/main.py](../../backend/main.py) — Auth HTTP endpoints

- [ ] `api_register` ([main.py:149](../../backend/main.py#L149)) — `POST /api/auth/register`
- [ ] `api_login` ([main.py:154](../../backend/main.py#L154)) — `POST /api/auth/login`
- [ ] `api_me` ([main.py:159](../../backend/main.py#L159)) — `GET /api/auth/me`
- [ ] `api_request_reset` ([main.py:170](../../backend/main.py#L170)) — `POST /api/auth/reset/request`
- [ ] `api_reset_password` ([main.py:175](../../backend/main.py#L175)) — `POST /api/auth/reset/confirm`
- [ ] `api_google_login_init` ([main.py:185](../../backend/main.py#L185)) — `GET /api/auth/google/init`
- [ ] `api_google_login_callback` ([main.py:208](../../backend/main.py#L208)) ⚠️ — `GET /api/auth/google/callback`

## 1.4 [legacy-frontend/landing.js](../../legacy-frontend/landing.js) — Frontend auth UI

- [ ] `showLanding` ([landing.js:39](../../legacy-frontend/landing.js#L39)) — แสดง landing page
- [ ] `showApp` ([landing.js:57](../../legacy-frontend/landing.js#L57)) — แสดง main app
- [ ] `_redirectToAppOrAdmin` ([landing.js:79](../../legacy-frontend/landing.js#L79)) — probe /admin → redirect
- [ ] `showAuthModal` ([landing.js:109](../../legacy-frontend/landing.js#L109)) — เปิด modal login/register
- [ ] `doLogin` ([landing.js:137](../../legacy-frontend/landing.js#L137)) — submit login form
- [ ] `doGoogleLogin` ([landing.js:188](../../legacy-frontend/landing.js#L188)) — redirect ไป Google OAuth
- [ ] `doRegister` ([landing.js:223](../../legacy-frontend/landing.js#L223)) — submit register form
- [ ] `doLogout` ([landing.js:265](../../legacy-frontend/landing.js#L265)) ⚠️ — เคลียร์ token + redirect (เคยลบ token ผิด — fix แล้ว v9.4.9)
- [ ] `doForgotPassword` ([landing.js:276](../../legacy-frontend/landing.js#L276)) — ขอรีเซ็ตรหัส
- [ ] `doResetPassword` ([landing.js:317](../../legacy-frontend/landing.js#L317)) — confirm รหัสใหม่
- [ ] `_handleGoogleLoginFragment` ([landing.js:368](../../legacy-frontend/landing.js#L368)) 🔥 — parse `#token=` + save JWT
- [ ] `_handleGoogleLoginError` ([landing.js:427](../../legacy-frontend/landing.js#L427))
- [ ] `_redirectToPendingLineLink` ([landing.js:27](../../legacy-frontend/landing.js#L27)) — redirect ไป LINE link หลัง login
- [ ] `initAuth` ([landing.js:449](../../legacy-frontend/landing.js#L449)) 🔥 — entry point — เรียกตอน DOMContentLoaded

---

# 2. 📤 Upload + Queue

> **บทบาท:** รับไฟล์จาก browser → ลง disk → enqueue → background worker ประมวลผล → progress UI
> **ฟังก์ชัน:** 39 · **อันตราย:** ⚠️ `upload_files` 180 บรรทัด · เป็น hotspot สูงสุดในระบบ

## 2.1 [backend/main.py](../../backend/main.py) — Upload endpoints

- [ ] `_make_skip` ([main.py:468](../../backend/main.py#L468)) — สร้าง skip-record สำหรับ duplicate
- [ ] `_get_user_quota_lock` ([main.py:492](../../backend/main.py#L492)) — per-user lock กัน race quota
- [ ] `upload_files` ([main.py:502](../../backend/main.py#L502)) ⚠️🔥 — **180 บรรทัด** — multi-file upload + dedup + enqueue
- [ ] `_guess_mime` ([main.py:703](../../backend/main.py#L703)) — เดา MIME จาก extension
- [ ] `_push_uploads_to_drive` ([main.py:722](../../backend/main.py#L722)) — push raw file ขึ้น Drive (BYOS)
- [ ] `_cleanup_drive_for_deleted_file` ([main.py:758](../../backend/main.py#L758))
- [ ] `_why_slow` ([main.py:803](../../backend/main.py#L803)) — explain slow upload reason
- [ ] `upload_status` ([main.py:832](../../backend/main.py#L832)) ⚠️ — **126 บรรทัด** — รวม queue + active + done
- [ ] `retry_upload` ([main.py:961](../../backend/main.py#L961)) — retry job ที่ fail
- [ ] `dismiss_upload_error` ([main.py:1011](../../backend/main.py#L1011)) — ปิด error item
- [ ] `cancel_upload` ([main.py:1046](../../backend/main.py#L1046)) — ยกเลิก job
- [ ] `healthz_queue` ([main.py:1087](../../backend/main.py#L1087)) — queue health endpoint
- [ ] `skip_duplicates` ([main.py:2367](../../backend/main.py#L2367)) — ยืนยัน/ข้าม dup batch

## 2.2 [backend/upload_worker.py](../../backend/upload_worker.py) — Background worker

- [ ] `get_priority_class` ([upload_worker.py:87](../../backend/upload_worker.py#L87)) — class 1/2/3 ตาม ext
- [ ] `get_avg_sec` ([upload_worker.py:97](../../backend/upload_worker.py#L97)) — rolling avg (มี 60s cap v9.4.8)
- [ ] `update_avg_sec` ([upload_worker.py:105](../../backend/upload_worker.py#L105))
- [ ] `start_worker` ([upload_worker.py:126](../../backend/upload_worker.py#L126)) — start background task
- [ ] `stop_worker` ([upload_worker.py:155](../../backend/upload_worker.py#L155))
- [ ] `get_worker_health` ([upload_worker.py:169](../../backend/upload_worker.py#L169))
- [ ] `_heartbeat_loop` ([upload_worker.py:201](../../backend/upload_worker.py#L201)) — เขียน heartbeat ทุก 30s
- [ ] `_worker_loop` ([upload_worker.py:221](../../backend/upload_worker.py#L221)) 🔥 — main loop
- [ ] `_write_heartbeat` ([upload_worker.py:252](../../backend/upload_worker.py#L252))
- [ ] `_read_heartbeat` ([upload_worker.py:265](../../backend/upload_worker.py#L265))
- [ ] `_claim_next_job` ([upload_worker.py:275](../../backend/upload_worker.py#L275)) ⚠️ — atomic claim (กัน race)
- [ ] `_process_job` ([upload_worker.py:362](../../backend/upload_worker.py#L362)) 🔥 — full pipeline ต่อ 1 job
- [ ] `_write_progress` ([upload_worker.py:487](../../backend/upload_worker.py#L487)) — update progress %
- [ ] `_mark_job_failed` ([upload_worker.py:509](../../backend/upload_worker.py#L509))
- [ ] `format_user_error` ([upload_worker.py:561](../../backend/upload_worker.py#L561)) — i18n error CODE
- [ ] `_recover_stale_jobs` ([upload_worker.py:603](../../backend/upload_worker.py#L603)) — startup recovery (v9.4.5)
- [ ] `_push_to_drive_if_byos` ([upload_worker.py:641](../../backend/upload_worker.py#L641))
- [ ] `_guess_mime_for_drive` ([upload_worker.py:714](../../backend/upload_worker.py#L714))

## 2.3 [legacy-frontend/app.js](../../legacy-frontend/app.js) — Upload UI

- [ ] `initUpload` ([app.js:1520](../../legacy-frontend/app.js#L1520)) — wire upload button + dropzone
- [ ] `uploadFiles` ([app.js:1572](../../legacy-frontend/app.js#L1572)) — entry สำหรับหลายไฟล์
- [ ] `uploadOne` ([app.js:1628](../../legacy-frontend/app.js#L1628)) — upload ทีละไฟล์
- [ ] `baseMsg` ([app.js:1599](../../legacy-frontend/app.js#L1599)) / `worker` ([app.js:1661](../../legacy-frontend/app.js#L1661))
- [ ] `updateProgressUI` ([app.js:1618](../../legacy-frontend/app.js#L1618))
- [ ] `localizeError` ([app.js:1793](../../legacy-frontend/app.js#L1793)) / `localizeBackendStep` ([app.js:1820](../../legacy-frontend/app.js#L1820))
- [ ] `UploadTray` ([app.js:1830](../../legacy-frontend/app.js#L1830)) ⚠️ — class object (เป็น mini-module): `_ensureDom`, `_fetchStatus`, `openIfHasItems`, `_startPolling`, `tick`, `_render`, `_renderItem`, `_onRetry`, `_onDismiss`, `_onCancel`, `notifyEnqueued`
- [ ] `showDuplicateModal` ([app.js:2238](../../legacy-frontend/app.js#L2238)) — modal dup confirm
- [ ] `updateConfirmLabel` ([app.js:2312](../../legacy-frontend/app.js#L2312)) / `quickApplyAll` ([app.js:2327](../../legacy-frontend/app.js#L2327))
- [ ] `hideDuplicateModal` ([app.js:2339](../../legacy-frontend/app.js#L2339)) / `cancelPendingSkip` ([app.js:2348](../../legacy-frontend/app.js#L2348))
- [ ] `confirmDupActions` ([app.js:2372](../../legacy-frontend/app.js#L2372)) / `showUndoToast` ([app.js:2399](../../legacy-frontend/app.js#L2399))
- [ ] `fireSkipApi` ([app.js:2466](../../legacy-frontend/app.js#L2466))

---

# 3. 📄 Extraction + AI Ingest

> **บทบาท:** แกะข้อความจาก PDF/Word/Excel/PPT/รูป/เสียง/วิดีโอ → cleanup → chunk
> **ฟังก์ชัน:** 38 · **อันตราย:** ⚠️ การเปลี่ยน library extract → กระทบทุก format

## 3.1 [backend/extraction.py](../../backend/extraction.py) — Text extraction core

- [ ] `strip_surrogates` ([extraction.py:36](../../backend/extraction.py#L36)) — กัน UTF-16 surrogate (เคยพัง v9.3.4)
- [ ] `extract_text` ([extraction.py:76](../../backend/extraction.py#L76)) 🔥 — main dispatch (เลือก extractor ตาม format)
- [ ] `_extract_text_raw` ([extraction.py:99](../../backend/extraction.py#L99))
- [ ] `_safe_progress` ([extraction.py:166](../../backend/extraction.py#L166)) — progress callback wrapper
- [ ] `_extract_image_ocr` ([extraction.py:180](../../backend/extraction.py#L180)) — Tesseract OCR
- [ ] `_extract_pdf_with_fallbacks` ([extraction.py:215](../../backend/extraction.py#L215)) ⚠️ — docling → basic → OCR
- [ ] `classify_extraction_status` ([extraction.py:251](../../backend/extraction.py#L251)) — text/empty/error
- [ ] `_extract_with_docling` ([extraction.py:296](../../backend/extraction.py#L296))
- [ ] `_extract_pdf_basic` ([extraction.py:317](../../backend/extraction.py#L317)) — PyPDF
- [ ] `_extract_pdf_ocr` ([extraction.py:338](../../backend/extraction.py#L338)) — pdf2image + OCR
- [ ] `_extract_docx_basic` ([extraction.py:369](../../backend/extraction.py#L369))
- [ ] `_extract_txt` ([extraction.py:399](../../backend/extraction.py#L399))
- [ ] `cleanup_extracted_text` ([extraction.py:414](../../backend/extraction.py#L414)) — LLM cleanup pass
- [ ] `_llm_fix_chunk` ([extraction.py:455](../../backend/extraction.py#L455))
- [ ] `_postprocess_thai` ([extraction.py:480](../../backend/extraction.py#L480)) — แก้คำผิดไทย
- [ ] `_extract_xlsx` ([extraction.py:505](../../backend/extraction.py#L505))
- [ ] `_extract_pptx` ([extraction.py:536](../../backend/extraction.py#L536))
- [ ] `_extract_html` ([extraction.py:584](../../backend/extraction.py#L584))
- [ ] `_extract_json` ([extraction.py:621](../../backend/extraction.py#L621))
- [ ] `_extract_rtf` ([extraction.py:649](../../backend/extraction.py#L649))

## 3.2 [backend/ai_ingest.py](../../backend/ai_ingest.py) — Gemini multimodal

- [ ] `is_ai_format` ([ai_ingest.py:73](../../backend/ai_ingest.py#L73)) — รูป/เสียง/วิดีโอ?
- [ ] `is_available` ([ai_ingest.py:78](../../backend/ai_ingest.py#L78)) — มี GEMINI_API_KEY?
- [ ] `_safe_async_progress` ([ai_ingest.py:83](../../backend/ai_ingest.py#L83))
- [ ] `ingest_via_ai` ([ai_ingest.py:93](../../backend/ai_ingest.py#L93)) 🔥 — main dispatch
- [ ] `_upload_to_gemini` ([ai_ingest.py:137](../../backend/ai_ingest.py#L137))
- [ ] `_wait_for_file_active` ([ai_ingest.py:151](../../backend/ai_ingest.py#L151)) — poll until ACTIVE
- [ ] `_ingest_audio` ([ai_ingest.py:185](../../backend/ai_ingest.py#L185)) — Gemini 2.5 transcribe
- [ ] `_ingest_video` ([ai_ingest.py:226](../../backend/ai_ingest.py#L226))
- [ ] `_ingest_image_smart` ([ai_ingest.py:269](../../backend/ai_ingest.py#L269)) — vision + classification

## 3.3 [backend/text_chunker.py](../../backend/text_chunker.py) — Chunking

- [ ] `chunk_text` ([text_chunker.py:32](../../backend/text_chunker.py#L32)) 🔥 — main entry
- [ ] `_split_by_heading` ([text_chunker.py:64](../../backend/text_chunker.py#L64))
- [ ] `_split_by_paragraph` ([text_chunker.py:80](../../backend/text_chunker.py#L80))
- [ ] `_split_by_sentence` ([text_chunker.py:89](../../backend/text_chunker.py#L89))
- [ ] `_accumulate` ([text_chunker.py:95](../../backend/text_chunker.py#L95))
- [ ] `_merge_small` ([text_chunker.py:117](../../backend/text_chunker.py#L117))
- [ ] `_split_oversized` ([text_chunker.py:137](../../backend/text_chunker.py#L137))
- [ ] `_hard_split` ([text_chunker.py:148](../../backend/text_chunker.py#L148))
- [ ] `_add_overlap` ([text_chunker.py:153](../../backend/text_chunker.py#L153))

## 3.4 [backend/vault.py](../../backend/vault.py) — Vault searchable text

- [ ] `tokenize_filename` ([vault.py:45](../../backend/vault.py#L45))
- [ ] `build_vault_searchable_text` ([vault.py:74](../../backend/vault.py#L74))
- [ ] `is_vault_extracted_text` ([vault.py:111](../../backend/vault.py#L111))

---

# 4. 🗃️ Files + Organize

> **บทบาท:** CRUD ไฟล์ · จัดกลุ่ม (cluster) · สรุป (summary) · metadata · download
> **ฟังก์ชัน:** 50 · **อันตราย:** ⚠️ `delete_file` ต้องระวัง Drive cleanup

## 4.1 [backend/main.py](../../backend/main.py) — File endpoints

- [ ] `organize` ([main.py:1155](../../backend/main.py#L1155)) — `POST /api/organize`
- [ ] `unprocessed_count` ([main.py:1180](../../backend/main.py#L1180))
- [ ] `organize_new` ([main.py:1198](../../backend/main.py#L1198))
- [ ] `list_files` ([main.py:1258](../../backend/main.py#L1258)) 🔥 — `GET /api/files`
- [ ] `list_clusters` ([main.py:1289](../../backend/main.py#L1289))
- [ ] `update_cluster` ([main.py:1354](../../backend/main.py#L1354))
- [ ] `get_summary` ([main.py:1371](../../backend/main.py#L1371))
- [ ] `get_file_content` ([main.py:1415](../../backend/main.py#L1415))
- [ ] `download_file` ([main.py:1463](../../backend/main.py#L1463))
- [ ] `create_share_link` ([main.py:1509](../../backend/main.py#L1509))
- [ ] `download_shared_file` ([main.py:1549](../../backend/main.py#L1549))
- [ ] `signed_download` ([main.py:1585](../../backend/main.py#L1585))
- [ ] `reprocess_file` ([main.py:2073](../../backend/main.py#L2073))
- [ ] `update_summary` ([main.py:2165](../../backend/main.py#L2165))
- [ ] `delete_file` ([main.py:2193](../../backend/main.py#L2193)) ⚠️ — ลบ + cleanup Drive + dec quota
- [ ] `promote_vault_file` ([main.py:2278](../../backend/main.py#L2278)) — promote vault → indexed
- [ ] `get_stats` ([main.py:3199](../../backend/main.py#L3199))
- [ ] `reset_all` ([main.py:3266](../../backend/main.py#L3266)) ⚠️ — **103 บรรทัด** — wipe user data

## 4.2 [backend/organizer.py](../../backend/organizer.py) — Clustering + summary

- [ ] `organize_files` ([organizer.py:16](../../backend/organizer.py#L16)) 🔥 — main entry
- [ ] `_cluster_files` ([organizer.py:200](../../backend/organizer.py#L200)) — LLM cluster
- [ ] `_generate_summary` ([organizer.py:255](../../backend/organizer.py#L255))
- [ ] `_generate_summary_simple` ([organizer.py:268](../../backend/organizer.py#L268))
- [ ] `_generate_summary_mapreduce` ([organizer.py:301](../../backend/organizer.py#L301)) — for big files
- [ ] `_summarize_chunk` ([organizer.py:348](../../backend/organizer.py#L348))
- [ ] `_merge_summaries` ([organizer.py:374](../../backend/organizer.py#L374))
- [ ] `_find_importance` ([organizer.py:417](../../backend/organizer.py#L417))
- [ ] `organize_new_files` ([organizer.py:431](../../backend/organizer.py#L431))

## 4.3 [backend/duplicate_detector.py](../../backend/duplicate_detector.py) 🟡 disabled v9.3.2

- [ ] `normalize_text` ([duplicate_detector.py:113](../../backend/duplicate_detector.py#L113))
- [ ] `compute_content_hash` ([duplicate_detector.py:127](../../backend/duplicate_detector.py#L127))
- [ ] `_extract_topics` ([duplicate_detector.py:155](../../backend/duplicate_detector.py#L155))
- [ ] `find_duplicate_for_file` ([duplicate_detector.py:176](../../backend/duplicate_detector.py#L176)) 🟡 — `_DEDUP_DISABLED=True`
- [ ] `detect_duplicates_for_batch` ([duplicate_detector.py:309](../../backend/duplicate_detector.py#L309)) 🟡

## 4.4 [backend/markdown_store.py](../../backend/markdown_store.py) — Summary .md files

- [ ] `write_summary_md` ([markdown_store.py:25](../../backend/markdown_store.py#L25))
- [ ] `read_summary_md` ([markdown_store.py:93](../../backend/markdown_store.py#L93))
- [ ] `list_all_summaries` ([markdown_store.py:118](../../backend/markdown_store.py#L118))
- [ ] `_safe_filename` ([markdown_store.py:131](../../backend/markdown_store.py#L131))

## 4.5 [backend/metadata.py](../../backend/metadata.py) — File metadata enrichment

- [ ] `enrich_file_metadata` ([metadata.py:14](../../backend/metadata.py#L14))
- [ ] `enrich_all_files` ([metadata.py:98](../../backend/metadata.py#L98))
- [ ] `get_file_metadata` ([metadata.py:114](../../backend/metadata.py#L114))
- [ ] `update_file_metadata` ([metadata.py:136](../../backend/metadata.py#L136))

## 4.6 [backend/shared_links.py](../../backend/shared_links.py) + [signed_urls.py](../../backend/signed_urls.py)

- [ ] `generate_share_token` ([shared_links.py:14](../../backend/shared_links.py#L14))
- [ ] `get_share_link` ([shared_links.py:37](../../backend/shared_links.py#L37))
- [ ] `build_share_url` ([shared_links.py:50](../../backend/shared_links.py#L50))
- [ ] `sign_download_token` ([signed_urls.py:45](../../backend/signed_urls.py#L45))
- [ ] `verify_download_token` ([signed_urls.py:76](../../backend/signed_urls.py#L76))

## 4.7 [legacy-frontend/app.js](../../legacy-frontend/app.js) — Files UI

- [ ] `loadFiles` ([app.js:2495](../../legacy-frontend/app.js#L2495))
- [ ] `updateFileFilterCounts` ([app.js:2508](../../legacy-frontend/app.js#L2508))
- [ ] `initFileFilterChips` ([app.js:2523](../../legacy-frontend/app.js#L2523))
- [ ] `promoteVaultFile` ([app.js:2544](../../legacy-frontend/app.js#L2544))
- [ ] `renderFileList` ([app.js:2565](../../legacy-frontend/app.js#L2565)) 🔥 — render หลัก
- [ ] `retryExtraction` ([app.js:2652](../../legacy-frontend/app.js#L2652))
- [ ] `deleteFile` ([app.js:2668](../../legacy-frontend/app.js#L2668))
- [ ] `openFileDetail` ([app.js:2691](../../legacy-frontend/app.js#L2691))
- [ ] `closeFileDetail` ([app.js:2758](../../legacy-frontend/app.js#L2758))
- [ ] `toggleSummaryEdit` ([app.js:2805](../../legacy-frontend/app.js#L2805))
- [ ] `saveSummaryEdit` ([app.js:2835](../../legacy-frontend/app.js#L2835))
- [ ] `loadUnprocessedCount` ([app.js:2867](../../legacy-frontend/app.js#L2867))
- [ ] `runOrganizeAll` ([app.js:2884](../../legacy-frontend/app.js#L2884))
- [ ] `runOrganizeNew` ([app.js:2911](../../legacy-frontend/app.js#L2911))
- [ ] `editCluster` ([app.js:3070](../../legacy-frontend/app.js#L3070))
- [ ] `saveCluster` ([app.js:3116](../../legacy-frontend/app.js#L3116))

---

# 5. 🧠 Knowledge Graph + Search

> **บทบาท:** ดูดความสัมพันธ์ระหว่างไฟล์ → graph · ค้นแบบ keyword/semantic/hybrid · RAG chat
> **ฟังก์ชัน:** 35

## 5.1 [backend/graph_builder.py](../../backend/graph_builder.py)

- [ ] `build_full_graph` ([graph_builder.py:21](../../backend/graph_builder.py#L21)) 🔥 — rebuild ทั้ง graph
- [ ] `get_graph_data` ([graph_builder.py:368](../../backend/graph_builder.py#L368)) — nodes+edges
- [ ] `get_node_detail` ([graph_builder.py:409](../../backend/graph_builder.py#L409))
- [ ] `get_neighborhood` ([graph_builder.py:520](../../backend/graph_builder.py#L520))

## 5.2 [backend/relations.py](../../backend/relations.py)

- [ ] `get_backlinks` ([relations.py:12](../../backend/relations.py#L12))
- [ ] `get_outgoing` ([relations.py:38](../../backend/relations.py#L38))
- [ ] `get_suggestions` ([relations.py:64](../../backend/relations.py#L64))
- [ ] `accept_suggestion` ([relations.py:99](../../backend/relations.py#L99))
- [ ] `dismiss_suggestion` ([relations.py:130](../../backend/relations.py#L130))
- [ ] `generate_suggestions` ([relations.py:148](../../backend/relations.py#L148))

## 5.3 [backend/vector_search.py](../../backend/vector_search.py) — TF-IDF

- [ ] `chunk_text` ([vector_search.py:20](../../backend/vector_search.py#L20)) — local copy
- [ ] `_split_sentences` ([vector_search.py:65](../../backend/vector_search.py#L65))
- [ ] `_tokenize` ([vector_search.py:71](../../backend/vector_search.py#L71))
- [ ] `_compute_tf` ([vector_search.py:79](../../backend/vector_search.py#L79))
- [ ] `index_file` ([vector_search.py:86](../../backend/vector_search.py#L86)) 🔥 — index ทุกครั้งที่ extract เสร็จ
- [ ] `_rebuild_idf` ([vector_search.py:121](../../backend/vector_search.py#L121))
- [ ] `search` ([vector_search.py:140](../../backend/vector_search.py#L140))
- [ ] `keyword_search` ([vector_search.py:202](../../backend/vector_search.py#L202))
- [ ] `hybrid_search` ([vector_search.py:251](../../backend/vector_search.py#L251))
- [ ] `remove_file` ([vector_search.py:303](../../backend/vector_search.py#L303))
- [ ] `is_available` ([vector_search.py:332](../../backend/vector_search.py#L332))

## 5.4 [backend/retriever.py](../../backend/retriever.py) — RAG chat

- [ ] `chat_with_retrieval` ([retriever.py:36](../../backend/retriever.py#L36)) 🔥 — main RAG flow
- [ ] `_build_inventory` ([retriever.py:320](../../backend/retriever.py#L320))
- [ ] `_select_context` ([retriever.py:366](../../backend/retriever.py#L366))
- [ ] `_generate_answer` ([retriever.py:406](../../backend/retriever.py#L406))

## 5.5 [backend/main.py](../../backend/main.py) — Graph endpoints

- [ ] `chat` ([main.py:2469](../../backend/main.py#L2469)) — `POST /api/chat`
- [ ] `api_build_graph` ([main.py:3012](../../backend/main.py#L3012))
- [ ] `api_global_graph` ([main.py:3024](../../backend/main.py#L3024))
- [ ] `api_list_nodes` ([main.py:3031](../../backend/main.py#L3031))
- [ ] `api_get_node` ([main.py:3056](../../backend/main.py#L3056))
- [ ] `api_neighborhood` ([main.py:3065](../../backend/main.py#L3065))
- [ ] `api_list_edges` ([main.py:3077](../../backend/main.py#L3077))
- [ ] `api_backlinks` ([main.py:3106](../../backend/main.py#L3106))
- [ ] `api_outgoing` ([main.py:3112](../../backend/main.py#L3112))
- [ ] `api_suggestions` ([main.py:3118](../../backend/main.py#L3118))
- [ ] `api_accept_suggestion` ([main.py:3125](../../backend/main.py#L3125))
- [ ] `api_dismiss_suggestion` ([main.py:3134](../../backend/main.py#L3134))
- [ ] `api_get_metadata` ([main.py:3147](../../backend/main.py#L3147))
- [ ] `api_update_metadata` ([main.py:3156](../../backend/main.py#L3156))
- [ ] `api_enrich_metadata` ([main.py:3166](../../backend/main.py#L3166))
- [ ] `api_list_lenses` ([main.py:3181](../../backend/main.py#L3181))

## 5.6 [legacy-frontend/app.js](../../legacy-frontend/app.js) — Graph + Chat UI

- [ ] `initKnowledgeTabs` ([app.js:2952](../../legacy-frontend/app.js#L2952))
- [ ] `loadKnowledge` ([app.js:2963](../../legacy-frontend/app.js#L2963))
- [ ] `showNodeInGraph` ([app.js:3062](../../legacy-frontend/app.js#L3062))
- [ ] `getNodeRadius` ([app.js:3698](../../legacy-frontend/app.js#L3698))
- [ ] `initGraphControls` ([app.js:3702](../../legacy-frontend/app.js#L3702))
- [ ] `fitGraphToView` ([app.js:3826](../../legacy-frontend/app.js#L3826))
- [ ] `loadGraph` ([app.js:3848](../../legacy-frontend/app.js#L3848))
- [ ] `renderGraph` ([app.js:3873](../../legacy-frontend/app.js#L3873))
- [ ] `_doRenderGraph` ([app.js:3878](../../legacy-frontend/app.js#L3878)) ⚠️ — render หลัก (D3-like ~200 บรรทัด)
- [ ] `handleNodeHover` ([app.js:4079](../../legacy-frontend/app.js#L4079))
- [ ] `selectNode` ([app.js:4132](../../legacy-frontend/app.js#L4132))
- [ ] `initChat` ([app.js:4190](../../legacy-frontend/app.js#L4190))
- [ ] `sendMessage` ([app.js:4201](../../legacy-frontend/app.js#L4201))
- [ ] `addMessage` ([app.js:4257](../../legacy-frontend/app.js#L4257))
- [ ] `removeMessage` ([app.js:4272](../../legacy-frontend/app.js#L4272))
- [ ] `updateSourcesPanel` ([app.js:4276](../../legacy-frontend/app.js#L4276))
- [ ] `renderEvidenceGraph` ([app.js:4312](../../legacy-frontend/app.js#L4312))

---

# 6. 📦 Context Packs + Share

> **บทบาท:** เลือกไฟล์เป็นชุด → สร้าง pack สำหรับส่งให้ AI ภายนอก · share link สาธารณะ
> **ฟังก์ชัน:** 38

## 6.1 [backend/context_packs.py](../../backend/context_packs.py)

- [ ] `list_packs` ([context_packs.py:36](../../backend/context_packs.py#L36))
- [ ] `get_pack` ([context_packs.py:47](../../backend/context_packs.py#L47))
- [ ] `create_pack` ([context_packs.py:61](../../backend/context_packs.py#L61))
- [ ] `delete_pack` ([context_packs.py:173](../../backend/context_packs.py#L173))
- [ ] `regenerate_pack` ([context_packs.py:201](../../backend/context_packs.py#L201))
- [ ] `_generate_pack_content` ([context_packs.py:269](../../backend/context_packs.py#L269)) 🔥
- [ ] `get_pack_context_text` ([context_packs.py:312](../../backend/context_packs.py#L312))
- [ ] `_serialize_pack` ([context_packs.py:329](../../backend/context_packs.py#L329))

## 6.2 [backend/ai_pack_builder.py](../../backend/ai_pack_builder.py) — 3-step AI flow

- [ ] `_gc_expired` ([ai_pack_builder.py:59](../../backend/ai_pack_builder.py#L59))
- [ ] `_gen_session_id` ([ai_pack_builder.py:71](../../backend/ai_pack_builder.py#L71))
- [ ] `_gen_draft_id` ([ai_pack_builder.py:76](../../backend/ai_pack_builder.py#L76))
- [ ] `_build_inventory_for_clarify` ([ai_pack_builder.py:84](../../backend/ai_pack_builder.py#L84))
- [ ] `_build_inventory_for_propose` ([ai_pack_builder.py:146](../../backend/ai_pack_builder.py#L146))
- [ ] `clarify_prompt` ([ai_pack_builder.py:254](../../backend/ai_pack_builder.py#L254)) 🔥 — step 1
- [ ] `propose_pack` ([ai_pack_builder.py:368](../../backend/ai_pack_builder.py#L368)) 🔥 — step 2
- [ ] `confirm_pack` ([ai_pack_builder.py:538](../../backend/ai_pack_builder.py#L538)) 🔥 — step 3
- [ ] `discard_draft` ([ai_pack_builder.py:618](../../backend/ai_pack_builder.py#L618))

## 6.3 [backend/pack_share.py](../../backend/pack_share.py)

- [ ] `sign_share_token` ([pack_share.py:57](../../backend/pack_share.py#L57))
- [ ] `verify_share_token` ([pack_share.py:72](../../backend/pack_share.py#L72))
- [ ] `build_share_url` ([pack_share.py:94](../../backend/pack_share.py#L94))
- [ ] `mask_email` ([pack_share.py:99](../../backend/pack_share.py#L99))
- [ ] `create_share` ([pack_share.py:116](../../backend/pack_share.py#L116))
- [ ] `update_share_files` ([pack_share.py:169](../../backend/pack_share.py#L169))
- [ ] `revoke_share` ([pack_share.py:189](../../backend/pack_share.py#L189))
- [ ] `list_shares_for_pack` ([pack_share.py:207](../../backend/pack_share.py#L207))
- [ ] `get_preview` ([pack_share.py:221](../../backend/pack_share.py#L221))
- [ ] `claim_to_workspace` ([pack_share.py:346](../../backend/pack_share.py#L346)) 🔥
- [ ] `_serialize_share` ([pack_share.py:526](../../backend/pack_share.py#L526))
- [ ] **class** `ShareTokenError`

## 6.4 [backend/main.py](../../backend/main.py) — Pack endpoints

- [ ] `api_list_packs` / `api_create_pack` / `api_get_pack` / `api_delete_pack` / `api_regenerate_pack` ([main.py:2580-2623](../../backend/main.py#L2580))
- [ ] `api_ai_build_clarify` / `api_ai_build_propose` / `api_ai_build_confirm` / `api_ai_build_discard` ([main.py:2655-2772](../../backend/main.py#L2655))
- [ ] `api_pack_share_create` ([main.py:2787](../../backend/main.py#L2787))
- [ ] `api_pack_share_update` ([main.py:2839](../../backend/main.py#L2839))
- [ ] `api_pack_share_revoke` ([main.py:2856](../../backend/main.py#L2856))
- [ ] `api_pack_shares_list` ([main.py:2872](../../backend/main.py#L2872))
- [ ] `api_pack_share_preview` ([main.py:2884](../../backend/main.py#L2884))
- [ ] `api_pack_share_claim` ([main.py:2906](../../backend/main.py#L2906))
- [ ] `serve_shared_pack_page` ([main.py:2935](../../backend/main.py#L2935))

## 6.5 [legacy-frontend/app.js](../../legacy-frontend/app.js) + [shared_pack.js](../../legacy-frontend/shared_pack.js)

- [ ] `openCreatePackModal` ([app.js:3133](../../legacy-frontend/app.js#L3133))
- [ ] `closePackModal` ([app.js:3162](../../legacy-frontend/app.js#L3162))
- [ ] `submitCreatePack` ([app.js:3166](../../legacy-frontend/app.js#L3166))
- [ ] `deletePack` ([app.js:3215](../../legacy-frontend/app.js#L3215))
- [ ] `sharePack` ([app.js:3233](../../legacy-frontend/app.js#L3233))
- [ ] `_copyShareLinkToClipboard` ([app.js:3265](../../legacy-frontend/app.js#L3265))
- [ ] `_renderShareBar` ([app.js:3293](../../legacy-frontend/app.js#L3293))
- [ ] `copyShareLink` ([app.js:3325](../../legacy-frontend/app.js#L3325))
- [ ] `togglePackFiles` ([app.js:3330](../../legacy-frontend/app.js#L3330))
- [ ] `revokePackShare` ([app.js:3357](../../legacy-frontend/app.js#L3357))
- [ ] `closePackShareBar` ([app.js:3371](../../legacy-frontend/app.js#L3371))
- [ ] `regeneratePack` ([app.js:3379](../../legacy-frontend/app.js#L3379))
- [ ] `_aiSwitchView` ([app.js:3429](../../legacy-frontend/app.js#L3429))
- [ ] `openAIPackBuilder` ([app.js:3448](../../legacy-frontend/app.js#L3448))
- [ ] `closeAIPackBuilder` ([app.js:3456](../../legacy-frontend/app.js#L3456))
- [ ] `submitAIBuilderPrompt` ([app.js:3467](../../legacy-frontend/app.js#L3467))
- [ ] `_aiRenderClarify` ([app.js:3517](../../legacy-frontend/app.js#L3517))
- [ ] `submitClarification` ([app.js:3534](../../legacy-frontend/app.js#L3534))
- [ ] `skipClarify` ([app.js:3549](../../legacy-frontend/app.js#L3549))
- [ ] `_aiCallPropose` ([app.js:3553](../../legacy-frontend/app.js#L3553))
- [ ] `_aiRenderPreview` ([app.js:3593](../../legacy-frontend/app.js#L3593))
- [ ] `confirmAIDraft` ([app.js:3609](../../legacy-frontend/app.js#L3609))
- [ ] `retryAIDraft` ([app.js:3662](../../legacy-frontend/app.js#L3662))
- [ ] `backFromClarify` ([app.js:3674](../../legacy-frontend/app.js#L3674))
- [ ] `_showState` / `_showError` / `_escapeHtml` / `_formatBytes` / `_showToast` / `loadPreview` / `_renderPreview` ([shared_pack.js](../../legacy-frontend/shared_pack.js))

---

# 7. 💾 Storage Router (Local/Drive)

> **บทบาท:** เลือก storage = local disk หรือ user's Google Drive (BYOS)
> **ฟังก์ชัน:** 56 · **อันตราย:** ⚠️ data loss risk — `delete_drive_file_if_byos` ลบของ user จริง

## 7.1 [backend/storage_router.py](../../backend/storage_router.py)

- [ ] `drive_file_link` / `drive_folder_link` ([storage_router.py:52-59](../../backend/storage_router.py#L52))
- [ ] `_get_byos_user_with_connection` ([storage_router.py:71](../../backend/storage_router.py#L71))
- [ ] `_build_drive_client` ([storage_router.py:101](../../backend/storage_router.py#L101))
- [ ] `_is_refresh_failure` ([storage_router.py:117](../../backend/storage_router.py#L117))
- [ ] `_should_trash_drive_file` ([storage_router.py:135](../../backend/storage_router.py#L135))
- [ ] `_mark_drive_connection_errored` ([storage_router.py:140](../../backend/storage_router.py#L140))
- [ ] `_get_personal_folder_id` ([storage_router.py:163](../../backend/storage_router.py#L163))
- [ ] `_get_data_folder_id` ([storage_router.py:168](../../backend/storage_router.py#L168))
- [ ] `_get_summaries_folder_id` ([storage_router.py:173](../../backend/storage_router.py#L173))
- [ ] `push_profile_to_drive_if_byos` ([storage_router.py:180](../../backend/storage_router.py#L180))
- [ ] `push_graph_to_drive_if_byos` ([storage_router.py:220](../../backend/storage_router.py#L220))
- [ ] `push_clusters_to_drive_if_byos` ([storage_router.py:250](../../backend/storage_router.py#L250))
- [ ] `push_relations_to_drive_if_byos` ([storage_router.py:273](../../backend/storage_router.py#L273))
- [ ] `push_contexts_to_drive_if_byos` ([storage_router.py:295](../../backend/storage_router.py#L295))
- [ ] `push_summary_to_drive_if_byos` ([storage_router.py:320](../../backend/storage_router.py#L320))
- [ ] `push_extracted_text_to_drive_if_byos` ([storage_router.py:358](../../backend/storage_router.py#L358))
- [ ] `push_raw_file_to_drive_if_byos` ([storage_router.py:394](../../backend/storage_router.py#L394))
- [ ] `fetch_file_bytes` ([storage_router.py:450](../../backend/storage_router.py#L450)) 🔥 — download ทุก source
- [ ] `delete_drive_file_if_byos` ([storage_router.py:482](../../backend/storage_router.py#L482)) ⚠️
- [ ] `delete_extracted_text_from_drive_if_byos` ([storage_router.py:533](../../backend/storage_router.py#L533))
- [ ] `delete_summary_from_drive_if_byos` ([storage_router.py:567](../../backend/storage_router.py#L567))
- [ ] `init_drive_folder_layout` ([storage_router.py:604](../../backend/storage_router.py#L604))

## 7.2 [backend/drive_storage.py](../../backend/drive_storage.py) — Drive API wrapper

- [ ] `_escape` ([drive_storage.py:368](../../backend/drive_storage.py#L368))
- [ ] **class** `DriveClient` — `__init__`, `_from_service`, `ensure_folder`, `create_folder`, `upload_file`, `upload_json`, `update_file_content`, `download_file`, `download_text`, `download_json`, `delete_file`, `delete_file_permanent`, `list_folder`, `get_metadata`, `find_file_by_name`, `upsert_json_file`, `ensure_pdb_folder_structure`

## 7.3 [backend/drive_oauth.py](../../backend/drive_oauth.py) — BYOS OAuth

- [ ] `_cleanup_expired_states` ([drive_oauth.py:69](../../backend/drive_oauth.py#L69))
- [ ] `_get_fernet` ([drive_oauth.py:80](../../backend/drive_oauth.py#L80))
- [ ] `encrypt_refresh_token` ([drive_oauth.py:99](../../backend/drive_oauth.py#L99)) ⚠️ — secret crypto
- [ ] `decrypt_refresh_token` ([drive_oauth.py:104](../../backend/drive_oauth.py#L104))
- [ ] `_build_flow` ([drive_oauth.py:122](../../backend/drive_oauth.py#L122))
- [ ] `init_oauth` ([drive_oauth.py:151](../../backend/drive_oauth.py#L151))
- [ ] `handle_callback` ([drive_oauth.py:195](../../backend/drive_oauth.py#L195))
- [ ] `build_credentials_from_refresh_token` ([drive_oauth.py:269](../../backend/drive_oauth.py#L269))
- [ ] `revoke_refresh_token` ([drive_oauth.py:290](../../backend/drive_oauth.py#L290))
- [ ] `_reset_state_cache_for_testing` ([drive_oauth.py:317](../../backend/drive_oauth.py#L317))

## 7.4 [backend/drive_sync.py](../../backend/drive_sync.py) — Drive↔local sync

- [ ] `_parse_drive_time` ([drive_sync.py:59](../../backend/drive_sync.py#L59))
- [ ] `_format_drive_time` ([drive_sync.py:66](../../backend/drive_sync.py#L66))
- [ ] `_has_drift` ([drive_sync.py:73](../../backend/drive_sync.py#L73))
- [ ] `sync_user_drive` ([drive_sync.py:542](../../backend/drive_sync.py#L542)) 🔥
- [ ] **class** `DriveSync` — `__init__`, `_from_client`, `load_connection`, `run_full_sync`, `_push_local_to_drive`, `_pull_drive_to_local`, `_import_drive_file`, `_split_drive_name`

## 7.5 [backend/drive_layout.py](../../backend/drive_layout.py)

- [ ] `raw_path_for` / `extracted_path_for` / `summary_path_for` / `backup_path_for` / `is_google_native`

## 7.6 [backend/main.py](../../backend/main.py) — Drive endpoints

- [ ] `_byos_503_error` ([main.py:3817](../../backend/main.py#L3817))
- [ ] `api_drive_status` ([main.py:3834](../../backend/main.py#L3834))
- [ ] `api_drive_oauth_init` ([main.py:3872](../../backend/main.py#L3872))
- [ ] `api_drive_oauth_callback` ([main.py:3886](../../backend/main.py#L3886))
- [ ] `api_drive_disconnect` ([main.py:3977](../../backend/main.py#L3977))
- [ ] `api_set_storage_mode` ([main.py:4036](../../backend/main.py#L4036))
- [ ] `api_drive_sync` ([main.py:4086](../../backend/main.py#L4086))

## 7.7 [legacy-frontend/storage_mode.js](../../legacy-frontend/storage_mode.js)

- [ ] `initStorageMode` ([storage_mode.js:25](../../legacy-frontend/storage_mode.js#L25))
- [ ] `handleDriveCallbackParams` ([storage_mode.js:45](../../legacy-frontend/storage_mode.js#L45))
- [ ] `refreshDriveStatus` ([storage_mode.js:118](../../legacy-frontend/storage_mode.js#L118))
- [ ] `connectDrive` ([storage_mode.js:140](../../legacy-frontend/storage_mode.js#L140))
- [ ] `disconnectDrive` ([storage_mode.js:180](../../legacy-frontend/storage_mode.js#L180))
- [ ] `_friendlyDriveErrorReason` ([storage_mode.js:247](../../legacy-frontend/storage_mode.js#L247))
- [ ] `renderStorageModeUI` ([storage_mode.js:284](../../legacy-frontend/storage_mode.js#L284))
- [ ] `syncDriveNow` ([storage_mode.js:415](../../legacy-frontend/storage_mode.js#L415))
- [ ] `wireStorageModeEvents` ([storage_mode.js:457](../../legacy-frontend/storage_mode.js#L457))
- [ ] `renderDriveErrorBanner` ([storage_mode.js:474](../../legacy-frontend/storage_mode.js#L474))
- [ ] `wireDriveErrorBanner` ([storage_mode.js:515](../../legacy-frontend/storage_mode.js#L515))
- [ ] `setupDriveStatusVisibilityPolling` ([storage_mode.js:553](../../legacy-frontend/storage_mode.js#L553))
- [ ] `formatRelativeTime` ([storage_mode.js:571](../../legacy-frontend/storage_mode.js#L571))

---

# 8. 💬 LINE Bot

> **บทบาท:** webhook LINE event → ตอบกลับ + อัปไฟล์ · account-link UI
> **ฟังก์ชัน:** 50

## 8.1 [backend/line_bot.py](../../backend/line_bot.py) — Webhook handler

- [ ] `verify_signature` ([line_bot.py:33](../../backend/line_bot.py#L33)) — verify HMAC
- [ ] `handle_line_event` ([line_bot.py:60](../../backend/line_bot.py#L60)) 🔥 — main dispatch
- [ ] `_handle_follow` ([line_bot.py:93](../../backend/line_bot.py#L93))
- [ ] `_handle_account_link` ([line_bot.py:135](../../backend/line_bot.py#L135))
- [ ] `_send_welcome_flow` ([line_bot.py:212](../../backend/line_bot.py#L212))
- [ ] `_handle_message` ([line_bot.py:293](../../backend/line_bot.py#L293))
- [ ] `_reply_not_linked` ([line_bot.py:335](../../backend/line_bot.py#L335))
- [ ] `_handle_text_message` ([line_bot.py:378](../../backend/line_bot.py#L378))
- [ ] `_handle_file_message` ([line_bot.py:439](../../backend/line_bot.py#L439)) ⚠️ — รับไฟล์จาก LINE
- [ ] `_auto_organize_after_upload` ([line_bot.py:580](../../backend/line_bot.py#L580))
- [ ] `_handle_unfollow` ([line_bot.py:638](../../backend/line_bot.py#L638))
- [ ] `_handle_postback` ([line_bot.py:653](../../backend/line_bot.py#L653))
- [ ] `_handle_group_join` ([line_bot.py:778](../../backend/line_bot.py#L778))
- [ ] `_ignore` / `_handle_unknown` ([line_bot.py:822-826](../../backend/line_bot.py#L822))

## 8.2 [backend/bot_adapters.py](../../backend/bot_adapters.py) — Bot abstraction

- [ ] `_mime_to_ext` ([bot_adapters.py:362](../../backend/bot_adapters.py#L362))
- [ ] `get_line_adapter` ([bot_adapters.py:366](../../backend/bot_adapters.py#L366))
- [ ] **class** `BotMessage` / `BotAttachment` (dataclass)
- [ ] **class** `BotAdapter` (abstract) — `platform_name`, `send_message`, `reply_message`, `download_attachment`, `show_typing`
- [ ] **class** `NoopBotAdapter` (testing) — 4 methods
- [ ] **class** `LineBotAdapter` — `__init__`, `_headers`, `_convert_message`, `send_message`, `reply_message`, `download_attachment`, `show_typing`, `issue_link_token`, `get_user_profile`

## 8.3 [backend/bot_handlers.py](../../backend/bot_handlers.py) — Intent dispatch

- [ ] `detect_intent` ([bot_handlers.py:80](../../backend/bot_handlers.py#L80)) 🔥
- [ ] `handle_text_intent` ([bot_handlers.py:147](../../backend/bot_handlers.py#L147))
- [ ] `_handle_list_files` ([bot_handlers.py:184](../../backend/bot_handlers.py#L184))
- [ ] `_handle_stats` ([bot_handlers.py:285](../../backend/bot_handlers.py#L285))
- [ ] `_handle_help` / `_handle_upload_help` / `_handle_settings` / `_handle_contact`
- [ ] `_handle_search` ([bot_handlers.py:378](../../backend/bot_handlers.py#L378))
- [ ] `_handle_url_prompt` ([bot_handlers.py:426](../../backend/bot_handlers.py#L426))
- [ ] `handle_url_upload` ([bot_handlers.py:446](../../backend/bot_handlers.py#L446))
- [ ] `_handle_get_file` ([bot_handlers.py:541](../../backend/bot_handlers.py#L541))
- [ ] `strip_markdown` ([bot_handlers.py:605](../../backend/bot_handlers.py#L605))
- [ ] `_handle_chat` ([bot_handlers.py:623](../../backend/bot_handlers.py#L623))
- [ ] **class** `Intent` (enum)

## 8.4 [backend/bot_messages.py](../../backend/bot_messages.py) — Flex message templates

- [ ] `link_prompt_card` ([bot_messages.py:26](../../backend/bot_messages.py#L26))
- [ ] `vault_status_card` ([bot_messages.py:104](../../backend/bot_messages.py#L104))
- [ ] `file_upload_confirmation_card` ([bot_messages.py:190](../../backend/bot_messages.py#L190))
- [ ] `error_card` ([bot_messages.py:294](../../backend/bot_messages.py#L294))
- [ ] `file_search_carousel` ([bot_messages.py:340](../../backend/bot_messages.py#L340))
- [ ] `_file_search_bubble` ([bot_messages.py:378](../../backend/bot_messages.py#L378))
- [ ] `text_with_quick_replies` ([bot_messages.py:451](../../backend/bot_messages.py#L451))
- [ ] `_info_row` / `_filetype_icon`

## 8.5 [backend/line_quota.py](../../backend/line_quota.py)

- [ ] `_current_month_key` / `record_push` / `get_current_usage` / `reset`

## 8.6 [backend/main.py](../../backend/main.py) — LINE endpoints

- [ ] `line_webhook` ([main.py:1671](../../backend/main.py#L1671)) 🔥
- [ ] `line_quota_status` ([main.py:1714](../../backend/main.py#L1714))
- [ ] `line_status` ([main.py:1840](../../backend/main.py#L1840))
- [ ] `line_connect` ([main.py:1896](../../backend/main.py#L1896))
- [ ] `line_disconnect` ([main.py:1923](../../backend/main.py#L1923))
- [ ] `serve_auth_line` ([main.py:1956](../../backend/main.py#L1956))
- [ ] `line_confirm_link` ([main.py:1966](../../backend/main.py#L1966)) ⚠️ — **104 บรรทัด**

## 8.7 [legacy-frontend/auth-line.js](../../legacy-frontend/auth-line.js) + [line_ui.js](../../legacy-frontend/line_ui.js)

- [ ] `setState` / `showActions` / `startCountdown` / `stopCountdown` / `getQueryParam` / `getToken` / `init` / `doConfirmLink` ([auth-line.js](../../legacy-frontend/auth-line.js))
- [ ] `loadLineStatus` ([line_ui.js:12](../../legacy-frontend/line_ui.js#L12)) ⚠️ — เป็นต้นเหตุของ race condition v9.4.3 → v9.4.9
- [ ] `_renderLineStatus` ([line_ui.js:31](../../legacy-frontend/line_ui.js#L31))
- [ ] `connectLine` ([line_ui.js:93](../../legacy-frontend/line_ui.js#L93))
- [ ] `disconnectLine` ([line_ui.js:119](../../legacy-frontend/line_ui.js#L119))
- [ ] `openLineChat` ([line_ui.js:140](../../legacy-frontend/line_ui.js#L140))

---

# 9. 🤖 MCP Server

> **บทบาท:** AI ภายนอก (ChatGPT/Claude/Cursor) เชื่อม MCP → เรียก tool อ่าน/เขียนข้อมูล
> **ฟังก์ชัน:** 41

## 9.1 [backend/mcp_tools.py](../../backend/mcp_tools.py) — 18 tools

- [ ] `call_tool` ([mcp_tools.py:339](../../backend/mcp_tools.py#L339)) 🔥 — dispatcher
- [ ] `_tool_get_profile` ([mcp_tools.py:496](../../backend/mcp_tools.py#L496))
- [ ] `_tool_list_files` ([mcp_tools.py:542](../../backend/mcp_tools.py#L542))
- [ ] `_tool_get_file_content` ([mcp_tools.py:573](../../backend/mcp_tools.py#L573))
- [ ] `_tool_get_file_link` ([mcp_tools.py:607](../../backend/mcp_tools.py#L607))
- [ ] `_tool_get_file_summary` ([mcp_tools.py:655](../../backend/mcp_tools.py#L655))
- [ ] `_tool_list_collections` ([mcp_tools.py:683](../../backend/mcp_tools.py#L683))
- [ ] `_tool_list_context_packs` ([mcp_tools.py:716](../../backend/mcp_tools.py#L716))
- [ ] `_tool_get_context_pack` ([mcp_tools.py:734](../../backend/mcp_tools.py#L734))
- [ ] `_tool_search_knowledge` ([mcp_tools.py:757](../../backend/mcp_tools.py#L757))
- [ ] `_tool_explore_graph` ([mcp_tools.py:890](../../backend/mcp_tools.py#L890))
- [ ] `_tool_create_context_pack` ([mcp_tools.py:983](../../backend/mcp_tools.py#L983))
- [ ] `_tool_add_note` ([mcp_tools.py:1016](../../backend/mcp_tools.py#L1016))
- [ ] `_tool_update_file_tags` ([mcp_tools.py:1059](../../backend/mcp_tools.py#L1059))
- [ ] `_tool_get_overview` ([mcp_tools.py:1093](../../backend/mcp_tools.py#L1093))
- [ ] `_tool_admin_login` ([mcp_tools.py:1132](../../backend/mcp_tools.py#L1132))
- [ ] `_tool_delete_file` ([mcp_tools.py:1146](../../backend/mcp_tools.py#L1146))
- [ ] `_tool_delete_pack` ([mcp_tools.py:1217](../../backend/mcp_tools.py#L1217))
- [ ] `_tool_run_organize` ([mcp_tools.py:1229](../../backend/mcp_tools.py#L1229))
- [ ] `_tool_build_graph` ([mcp_tools.py:1244](../../backend/mcp_tools.py#L1244))
- [ ] `_tool_enrich_metadata` ([mcp_tools.py:1259](../../backend/mcp_tools.py#L1259))
- [ ] `_tool_update_profile` ([mcp_tools.py:1284](../../backend/mcp_tools.py#L1284))
- [ ] `_tool_upload_text` ([mcp_tools.py:1352](../../backend/mcp_tools.py#L1352))
- [ ] `get_usage_logs` ([mcp_tools.py:1408](../../backend/mcp_tools.py#L1408))
- [ ] `_tool_reprocess_file` ([mcp_tools.py:1447](../../backend/mcp_tools.py#L1447))
- [ ] `_tool_export_file_to_chat` ([mcp_tools.py:1518](../../backend/mcp_tools.py#L1518))

## 9.2 [backend/mcp_tokens.py](../../backend/mcp_tokens.py)

- [ ] `_hash_token` / `generate_token` / `validate_token` / `list_tokens` / `revoke_token` / `get_active_token_count`

## 9.3 [backend/main.py](../../backend/main.py) — MCP endpoints

- [ ] `api_mcp_info` ([main.py:3384](../../backend/main.py#L3384))
- [ ] `api_generate_token` ([main.py:3402](../../backend/main.py#L3402))
- [ ] `api_list_tokens` ([main.py:3413](../../backend/main.py#L3413))
- [ ] `api_revoke_token` ([main.py:3420](../../backend/main.py#L3420))
- [ ] `api_test_connection` ([main.py:3429](../../backend/main.py#L3429))
- [ ] `api_mcp_tool_call` ([main.py:3453](../../backend/main.py#L3453))
- [ ] `api_mcp_logs` ([main.py:3481](../../backend/main.py#L3481))
- [ ] `api_get_permissions` ([main.py:3499](../../backend/main.py#L3499))
- [ ] `api_set_permissions` ([main.py:3505](../../backend/main.py#L3505))
- [ ] `_serialize_file` ([main.py:3517](../../backend/main.py#L3517))
- [ ] `_build_mcp_tools_list` ([main.py:3585](../../backend/main.py#L3585))
- [ ] `mcp_streamable_http` ([main.py:3620](../../backend/main.py#L3620)) ⚠️ — **136 บรรทัด** — custom protocol

## 9.4 [legacy-frontend/app.js](../../legacy-frontend/app.js) — MCP UI

- [ ] `initMCP` ([app.js:4902](../../legacy-frontend/app.js#L4902))
- [ ] `switchMcpTab` ([app.js:4944](../../legacy-frontend/app.js#L4944))
- [ ] `loadMCPSetup` ([app.js:4953](../../legacy-frontend/app.js#L4953))
- [ ] `renderMCPTools` ([app.js:5023](../../legacy-frontend/app.js#L5023))
- [ ] `toggleToolPermission` ([app.js:5097](../../legacy-frontend/app.js#L5097))
- [ ] `generateMCPToken` ([app.js:5119](../../legacy-frontend/app.js#L5119))
- [ ] `testMCPConnection` ([app.js:5171](../../legacy-frontend/app.js#L5171))
- [ ] `copyToClipboard` ([app.js:5225](../../legacy-frontend/app.js#L5225))
- [ ] `loadTokens` ([app.js:5243](../../legacy-frontend/app.js#L5243))
- [ ] `renderTokenList` ([app.js:5253](../../legacy-frontend/app.js#L5253))
- [ ] `revokeTokenAction` ([app.js:5307](../../legacy-frontend/app.js#L5307))
- [ ] `loadMCPLogs` ([app.js:5323](../../legacy-frontend/app.js#L5323))
- [ ] `renderMCPLogs` ([app.js:5340](../../legacy-frontend/app.js#L5340))

---

# 10. 👤 Profile + Personality + Context Memory

> **บทบาท:** เก็บข้อมูลตัวตน user (MBTI/Enneagram/Clifton/VIA) + context memory · ใช้ใส่ใน LLM prompt
> **ฟังก์ชัน:** 32

## 10.1 [backend/profile.py](../../backend/profile.py)

- [ ] `get_profile` ([profile.py:26](../../backend/profile.py#L26))
- [ ] `_safe_json_loads` ([profile.py:75](../../backend/profile.py#L75))
- [ ] `update_profile` ([profile.py:93](../../backend/profile.py#L93))
- [ ] `record_personality_history` ([profile.py:237](../../backend/profile.py#L237))
- [ ] `list_personality_history` ([profile.py:258](../../backend/profile.py#L258))
- [ ] `get_profile_context_text` ([profile.py:294](../../backend/profile.py#L294)) — สำหรับใส่ใน LLM prompt
- [ ] `is_profile_complete` ([profile.py:327](../../backend/profile.py#L327))

## 10.2 [backend/personality.py](../../backend/personality.py)

- [ ] `validate_mbti` ([personality.py:159](../../backend/personality.py#L159))
- [ ] `get_enneagram_wings` ([personality.py:175](../../backend/personality.py#L175))
- [ ] `validate_enneagram` ([personality.py:190](../../backend/personality.py#L190))
- [ ] `validate_clifton` ([personality.py:201](../../backend/personality.py#L201))
- [ ] `validate_via` ([personality.py:219](../../backend/personality.py#L219))
- [ ] `format_personality_for_llm` ([personality.py:235](../../backend/personality.py#L235))
- [ ] `build_personality_summary` ([personality.py:275](../../backend/personality.py#L275))
- [ ] `get_test_links` ([personality.py:316](../../backend/personality.py#L316))

## 10.3 [backend/context_memory.py](../../backend/context_memory.py)

- [ ] `save_context` / `load_context` / `list_contexts` / `update_context` / `delete_context`
- [ ] `auto_context` ([context_memory.py:276](../../backend/context_memory.py#L276)) 🔥 — AI สร้าง context อัตโนมัติ
- [ ] `get_active_contexts_for_profile` ([context_memory.py:313](../../backend/context_memory.py#L313))
- [ ] `_auto_summary` / `_auto_archive` / `_to_dict` / `_to_summary_dict` / `_safe_json`

## 10.4 [backend/main.py](../../backend/main.py)

- [ ] `api_get_profile` ([main.py:2487](../../backend/main.py#L2487))
- [ ] `api_personality_reference` ([main.py:2492](../../backend/main.py#L2492))
- [ ] `api_get_personality_history` ([main.py:2528](../../backend/main.py#L2528))
- [ ] `api_update_profile` ([main.py:2544](../../backend/main.py#L2544))
- [ ] `api_list_contexts` ([main.py:2945](../../backend/main.py#L2945))
- [ ] `api_save_context` ([main.py:2958](../../backend/main.py#L2958))
- [ ] `api_update_context` ([main.py:2975](../../backend/main.py#L2975))
- [ ] `api_delete_context` ([main.py:2985](../../backend/main.py#L2985))
- [ ] `api_get_context` ([main.py:2994](../../backend/main.py#L2994))

## 10.5 [legacy-frontend/app.js](../../legacy-frontend/app.js)

- [ ] `initProfile` ([app.js:4384](../../legacy-frontend/app.js#L4384))
- [ ] `ensurePersonalityReference` ([app.js:4423](../../legacy-frontend/app.js#L4423))
- [ ] `populatePersonalityDropdowns` ([app.js:4451](../../legacy-frontend/app.js#L4451))
- [ ] `ensureDatalist` ([app.js:4490](../../legacy-frontend/app.js#L4490))
- [ ] `renderRankList` ([app.js:4502](../../legacy-frontend/app.js#L4502))
- [ ] `renderTestLinks` ([app.js:4523](../../legacy-frontend/app.js#L4523))
- [ ] `updateEnneagramWingOptions` ([app.js:4540](../../legacy-frontend/app.js#L4540))
- [ ] `loadProfile` ([app.js:4566](../../legacy-frontend/app.js#L4566))
- [ ] `getMbtiInput` / `getEnneagramInput` / `_collectRankInputs` / `getCliftonInput` / `getViaInput`
- [ ] `saveProfile` ([app.js:4664](../../legacy-frontend/app.js#L4664))
- [ ] `refreshAllHistoryCounts` ([app.js:4718](../../legacy-frontend/app.js#L4718))
- [ ] `openPersonalityHistory` ([app.js:4748](../../legacy-frontend/app.js#L4748))
- [ ] `renderHistoryEntry` ([app.js:4779](../../legacy-frontend/app.js#L4779))
- [ ] `formatHistoryValue` ([app.js:4808](../../legacy-frontend/app.js#L4808))
- [ ] `loadContexts` ([app.js:5428](../../legacy-frontend/app.js#L5428))
- [ ] `_renderCtxCard` ([app.js:5462](../../legacy-frontend/app.js#L5462))
- [ ] `viewContext` ([app.js:5504](../../legacy-frontend/app.js#L5504))
- [ ] `openCtxModal` ([app.js:5528](../../legacy-frontend/app.js#L5528))
- [ ] `editContext` ([app.js:5561](../../legacy-frontend/app.js#L5561))
- [ ] `saveCtxModal` ([app.js:5563](../../legacy-frontend/app.js#L5563))
- [ ] `togglePin` ([app.js:5621](../../legacy-frontend/app.js#L5621))
- [ ] `deleteCtx` ([app.js:5640](../../legacy-frontend/app.js#L5640))

---

# 11. 💳 Billing + Plan Limits

> **บทบาท:** Stripe checkout/portal · เช็ค quota · lock data เมื่อ downgrade
> **ฟังก์ชัน:** 45

## 11.1 [backend/billing.py](../../backend/billing.py)

- [ ] `create_checkout_session` ([billing.py:31](../../backend/billing.py#L31)) 🔥
- [ ] `create_portal_session` ([billing.py:71](../../backend/billing.py#L71))
- [ ] `process_webhook` ([billing.py:87](../../backend/billing.py#L87)) ⚠️ — Stripe webhook
- [ ] `_find_user_by_customer` ([billing.py:186](../../backend/billing.py#L186))
- [ ] `_first_or_empty` ([billing.py:192](../../backend/billing.py#L192))
- [ ] `_handle_checkout_completed` ([billing.py:210](../../backend/billing.py#L210))
- [ ] `_handle_subscription_created` ([billing.py:271](../../backend/billing.py#L271))
- [ ] `_handle_subscription_updated` ([billing.py:296](../../backend/billing.py#L296))
- [ ] `_handle_subscription_deleted` ([billing.py:317](../../backend/billing.py#L317))
- [ ] `_handle_payment_succeeded` ([billing.py:411](../../backend/billing.py#L411))
- [ ] `_handle_payment_failed` ([billing.py:444](../../backend/billing.py#L444))
- [ ] `_map_stripe_status` ([billing.py:465](../../backend/billing.py#L465))
- [ ] `_ts_to_dt` ([billing.py:479](../../backend/billing.py#L479))
- [ ] `get_billing_info` ([billing.py:488](../../backend/billing.py#L488))

## 11.2 [backend/plan_limits.py](../../backend/plan_limits.py)

- [ ] `get_limits` ([plan_limits.py:103](../../backend/plan_limits.py#L103))
- [ ] `_effective_plan` ([plan_limits.py:109](../../backend/plan_limits.py#L109))
- [ ] `_get_billing_period_start` ([plan_limits.py:148](../../backend/plan_limits.py#L148))
- [ ] `_month_start_for_user` ([plan_limits.py:163](../../backend/plan_limits.py#L163))
- [ ] `get_file_count` / `get_storage_used_mb` / `get_pack_count`
- [ ] `get_monthly_summary_count` / `get_monthly_export_count` / `get_monthly_refresh_count` / `get_monthly_pack_share_count`
- [ ] `log_usage` ([plan_limits.py:270](../../backend/plan_limits.py#L270))
- [ ] `check_upload_allowed` ([plan_limits.py:282](../../backend/plan_limits.py#L282)) 🔥
- [ ] `check_pack_create_allowed` / `check_summary_allowed` / `check_export_allowed` / `check_pack_share_create_allowed` / `check_refresh_allowed` / `check_semantic_search_allowed`
- [ ] `get_usage_summary` ([plan_limits.py:411](../../backend/plan_limits.py#L411))
- [ ] `lock_excess_data` ([plan_limits.py:447](../../backend/plan_limits.py#L447)) ⚠️ — เมื่อ downgrade
- [ ] `unlock_data_for_plan` ([plan_limits.py:497](../../backend/plan_limits.py#L497))
- [ ] `log_audit` ([plan_limits.py:562](../../backend/plan_limits.py#L562))

## 11.3 [backend/main.py](../../backend/main.py)

- [ ] `api_create_checkout` ([main.py:3764](../../backend/main.py#L3764))
- [ ] `api_create_portal` ([main.py:3778](../../backend/main.py#L3778))
- [ ] `api_stripe_webhook` ([main.py:3790](../../backend/main.py#L3790))
- [ ] `api_billing_info` ([main.py:3795](../../backend/main.py#L3795))
- [ ] `api_get_usage` ([main.py:3255](../../backend/main.py#L3255))
- [ ] `api_get_plan_limits` ([main.py:3260](../../backend/main.py#L3260))
- [ ] `serve_billing_success` ([main.py:4139](../../backend/main.py#L4139))
- [ ] `serve_pricing` ([main.py:4145](../../backend/main.py#L4145))
- [ ] `serve_billing_cancelled` ([main.py:4156](../../backend/main.py#L4156))

## 11.4 [legacy-frontend/app.js](../../legacy-frontend/app.js)

- [ ] `initBilling` ([app.js:462](../../legacy-frontend/app.js#L462))
- [ ] `showPlanModal` ([app.js:475](../../legacy-frontend/app.js#L475))
- [ ] `closePlanModal` ([app.js:479](../../legacy-frontend/app.js#L479))
- [ ] `loadBillingInfo` ([app.js:483](../../legacy-frontend/app.js#L483))
- [ ] `updateBillingUI` ([app.js:494](../../legacy-frontend/app.js#L494))
- [ ] `doStarterCheckout` ([app.js:539](../../legacy-frontend/app.js#L539))
- [ ] `doOpenPortal` ([app.js:561](../../legacy-frontend/app.js#L561))
- [ ] `checkBillingRedirect` ([app.js:579](../../legacy-frontend/app.js#L579))
- [ ] `showUpgradeModal` ([app.js:138](../../legacy-frontend/app.js#L138)) — modal เมื่อชน quota
- [ ] `loadUsageInfo` ([app.js:380](../../legacy-frontend/app.js#L380))
- [ ] `renderUsageBars` ([app.js:392](../../legacy-frontend/app.js#L392))
- [ ] `updateUploadHint` ([app.js:423](../../legacy-frontend/app.js#L423))
- [ ] `updateSidebarStats` ([app.js:451](../../legacy-frontend/app.js#L451))

---

# 12. 🛠️ Admin + Misc + Infra

> **บทบาท:** หลังบ้าน · config · DB schema · LLM wrapper · admin panel
> **ฟังก์ชัน:** 60

## 12.1 [backend/admin.py](../../backend/admin.py)

- [ ] `get_admin_stats` ([admin.py:55](../../backend/admin.py#L55))
- [ ] `list_users` ([admin.py:176](../../backend/admin.py#L176))
- [ ] `get_user_detail` ([admin.py:260](../../backend/admin.py#L260))
- [ ] `_last_audit_id` ([admin.py:328](../../backend/admin.py#L328))
- [ ] `change_user_plan` ([admin.py:339](../../backend/admin.py#L339)) ⚠️
- [ ] `reset_user_password` ([admin.py:466](../../backend/admin.py#L466))
- [ ] `set_user_active` ([admin.py:543](../../backend/admin.py#L543))
- [ ] `set_user_admin` ([admin.py:595](../../backend/admin.py#L595))
- [ ] `list_audit_logs` ([admin.py:692](../../backend/admin.py#L692))

## 12.2 [backend/config.py](../../backend/config.py)

- [ ] `_generate_jwt_secret` ([config.py:48](../../backend/config.py#L48))
- [ ] `_load_or_create_mcp_secret` ([config.py:114](../../backend/config.py#L114))
- [ ] `is_byos_configured` ([config.py:156](../../backend/config.py#L156))
- [ ] `is_email_configured` ([config.py:174](../../backend/config.py#L174))
- [ ] `is_line_configured` ([config.py:190](../../backend/config.py#L190))
- [ ] `is_line_login_configured` ([config.py:197](../../backend/config.py#L197))
- [ ] `is_google_login_configured` ([config.py:212](../../backend/config.py#L212))

## 12.3 [backend/database.py](../../backend/database.py) — 26 SQLAlchemy models

- [ ] `gen_id` ([database.py:15](../../backend/database.py#L15))
- [ ] `init_db` ([database.py:596](../../backend/database.py#L596)) 🔥
- [ ] `get_db` ([database.py:1000](../../backend/database.py#L1000)) — DI dependency
- [ ] **models:** `User`, `File`, `Cluster`, `FileClusterMap`, `FileInsight`, `FileSummary`, `ChatQuery`, `UserProfile`, `ContextPack`, `ContextInjectionLog`, `NoteObject`, `GraphNode`, `GraphEdge`, `SuggestedRelation`, `GraphLens`, `CanvasObject`, `PersonalityHistory`, `ContextMemory`, `MCPToken`, `MCPUsageLog`, `WebhookLog`, `UsageLog`, `AuditLog`, `DriveConnection`, `PackShare`, `LineUser`

## 12.4 [backend/llm.py](../../backend/llm.py) — OpenRouter wrapper

- [ ] `_call_openrouter` ([llm.py:16](../../backend/llm.py#L16))
- [ ] `call_llm` ([llm.py:68](../../backend/llm.py#L68))
- [ ] `call_llm_pro` ([llm.py:73](../../backend/llm.py#L73)) — Gemini 2.5 Pro
- [ ] `call_llm_json` ([llm.py:80](../../backend/llm.py#L80)) — force JSON output

## 12.5 [backend/email_service.py](../../backend/email_service.py)

- [ ] `_render_password_reset_html` / `_render_password_reset_text` / `_send_sync` / `send_password_reset_email`

## 12.6 [backend/main.py](../../backend/main.py) — App lifecycle + admin endpoints

- [ ] `startup` ([main.py:69](../../backend/main.py#L69)) 🔥 — init DB + worker + folders
- [ ] `shutdown` ([main.py:119](../../backend/main.py#L119)) — stop worker
- [ ] `api_admin_me` ([main.py:1736](../../backend/main.py#L1736))
- [ ] `api_admin_stats` ([main.py:1749](../../backend/main.py#L1749))
- [ ] `api_admin_list_users` / `api_admin_user_detail` / `api_admin_change_plan` / `api_admin_reset_password` / `api_admin_toggle_active` / `api_admin_toggle_admin` / `api_admin_audit_logs`

## 12.7 [backend/main.py](../../backend/main.py) — Static page serving

- [ ] `_serve_html` ([main.py:4166](../../backend/main.py#L4166))
- [ ] `serve_landing` ([main.py:4177](../../backend/main.py#L4177))
- [ ] `serve_app` ([main.py:4183](../../backend/main.py#L4183))
- [ ] `serve_admin` ([main.py:4189](../../backend/main.py#L4189))
- [ ] `serve_reset_password_page` ([main.py:4198](../../backend/main.py#L4198))
- [ ] `serve_legacy` ([main.py:4204](../../backend/main.py#L4204))
- [ ] `serve_legacy_static` ([main.py:4210](../../backend/main.py#L4210))
- [ ] `serve_guide_static` ([main.py:4222](../../backend/main.py#L4222))
- [ ] `serve_static` ([main.py:4231](../../backend/main.py#L4231)) ⚠️ — catch-all (ต้องอยู่หลังสุด)

## 12.8 [legacy-frontend/admin.js](../../legacy-frontend/admin.js)

- [ ] `adminFetch` / `init` / `setupNav` / `switchTab` / `loadDashboard` / `loadUsers`
- [ ] `renderUsersTable` / `planBadge` / `handleUserAction`
- [ ] `setupModals` / `openModal` / `closeModal`
- [ ] `openChangePlan` / `submitChangePlan`
- [ ] `openResetPassword` / `submitResetPassword` / `copyPasswordToClipboard`
- [ ] `openConfirmActive` / `openConfirmAdmin` / `submitConfirmAction`
- [ ] `loadAuditLogs`
- [ ] `escapeHtml` / `showToast` / `debounce` / `generateRandomPassword`

---

# 13. 📚 Frontend Misc

> **บทบาท:** UI shell — i18n, nav, modals, FABs, kebab menu, sidebar, guide
> **ฟังก์ชัน:** 30

## 13.1 [legacy-frontend/app.js](../../legacy-frontend/app.js) — Shared UI

- [ ] `_setVh` ([app.js:29](../../legacy-frontend/app.js#L29)) — CSS var --vh fix iOS
- [ ] `authFetch` ([app.js:94](../../legacy-frontend/app.js#L94)) 🔥 — fetch + Auth header + 401 handler (เพิ่ง fix v9.4.9)
- [ ] `showUploadResultModal` ([app.js:171](../../legacy-frontend/app.js#L171))
- [ ] `skipIcon` ([app.js:179](../../legacy-frontend/app.js#L179))
- [ ] `escHandler` ([app.js:231](../../legacy-frontend/app.js#L231))
- [ ] `showLoadingOverlay` / `hideLoadingOverlay` ([app.js:244-293](../../legacy-frontend/app.js#L244))
- [ ] `initAppData` ([app.js:318](../../legacy-frontend/app.js#L318)) 🔥
- [ ] `_revealAdminLinkIfAdmin` ([app.js:339](../../legacy-frontend/app.js#L339))
- [ ] `maybeShowRebrandNotice` ([app.js:366](../../legacy-frontend/app.js#L366))
- [ ] `el` ([app.js:453](../../legacy-frontend/app.js#L453)) — querySelector helper

## 13.2 i18n + Language

- [ ] `getLang` ([app.js:1207](../../legacy-frontend/app.js#L1207))
- [ ] `t` ([app.js:1215](../../legacy-frontend/app.js#L1215)) — translate
- [ ] `applyLanguage` ([app.js:1223](../../legacy-frontend/app.js#L1223)) ⚠️ — เคยอยู่ก่อน initAuth ทำให้เกิด race v9.4.3

## 13.3 Navigation + Layout

- [ ] `toggleKebab` ([app.js:1277](../../legacy-frontend/app.js#L1277))
- [ ] `initKebabMenus` ([app.js:1289](../../legacy-frontend/app.js#L1289))
- [ ] `initPageFABs` ([app.js:1312](../../legacy-frontend/app.js#L1312))
- [ ] `initSidebarMobile` ([app.js:1330](../../legacy-frontend/app.js#L1330))
- [ ] `initGlobalModalUX` ([app.js:1378](../../legacy-frontend/app.js#L1378))
- [ ] `initNavigation` ([app.js:1473](../../legacy-frontend/app.js#L1473))
- [ ] `switchPage` ([app.js:1482](../../legacy-frontend/app.js#L1482))
- [ ] `loadStats` ([app.js:1501](../../legacy-frontend/app.js#L1501))

## 13.4 Date/Format helpers

- [ ] `formatDate` ([app.js:5385](../../legacy-frontend/app.js#L5385))
- [ ] `formatDateTime` ([app.js:5394](../../legacy-frontend/app.js#L5394))
- [ ] `formatTimeAgo` ([app.js:5403](../../legacy-frontend/app.js#L5403))
- [ ] `escapeHtml` ([app.js:4892](../../legacy-frontend/app.js#L4892))

## 13.5 Toast + Confirm modal

- [ ] `showToast` ([app.js:4830](../../legacy-frontend/app.js#L4830))
- [ ] `showConfirm` ([app.js:4851](../../legacy-frontend/app.js#L4851))

## 13.6 Guide system

- [ ] `initGuideSystem` ([app.js:5703](../../legacy-frontend/app.js#L5703))
- [ ] `openGuide` ([app.js:5727](../../legacy-frontend/app.js#L5727))
- [ ] `closeGuide` ([app.js:5736](../../legacy-frontend/app.js#L5736))
- [ ] `renderGuideTab` ([app.js:5744](../../legacy-frontend/app.js#L5744))

---

# 📌 ไม่อยู่กลุ่มไหน / Pydantic models (main.py)

> models 27 ตัวสำหรับ request body validation:
- [ ] `RegisterRequest`, `LoginRequest`, `ResetRequestModel`, `ResetPasswordModel`, `ChatRequest`
- [ ] `MBTIData` (มี `_check_type`, `_check_source` validator)
- [ ] `EnneagramData` (มี `_check_core`, `_check_wing`)
- [ ] `ProfileRequest`, `ContextPackRequest`
- [ ] `AIBuilderClarifyRequest`, `AIBuilderClarification`, `AIBuilderProposeRequest`, `AIBuilderConfirmEdits`, `AIBuilderConfirmRequest`
- [ ] `PackShareCreateRequest`, `PackShareUpdateRequest`, `MetadataUpdateRequest`
- [ ] `AdminChangePlanRequest`, `AdminResetPasswordRequest`, `AdminToggleRequest` (มี `_check_reason` validator)
- [ ] `ClusterUpdateRequest`, `LineConfirmLinkRequest`, `SummaryUpdateRequest`, `SkipDuplicatesRequest`
- [ ] `MCPTokenRequest`, `MCPToolCallRequest`, `CheckoutRequest`

---

# 🔥 Hotspot Summary (ฟังก์ชันที่ "แตะแล้วลามทั้งระบบ")

ถ้าจะเริ่ม audit/refactor → เริ่มจาก 10 ตัวนี้ก่อน:

- [ ] [`upload_files`](../../backend/main.py#L502) ⚠️ 180 lines — entry point ของ pipeline ทั้งหมด
- [ ] [`_process_job`](../../backend/upload_worker.py#L362) — worker pipeline core
- [ ] [`mcp_streamable_http`](../../backend/main.py#L3620) ⚠️ 136 lines — MCP protocol
- [ ] [`get_current_user`](../../backend/auth.py#L165) — auth DI (ทุก endpoint ใช้)
- [ ] [`extract_text`](../../backend/extraction.py#L76) — format dispatcher
- [ ] [`handle_line_event`](../../backend/line_bot.py#L60) — LINE entry
- [ ] [`fetch_file_bytes`](../../backend/storage_router.py#L450) — local/Drive abstraction
- [ ] [`chat_with_retrieval`](../../backend/retriever.py#L36) — RAG main flow
- [ ] [`authFetch`](../../legacy-frontend/app.js#L94) — ทุก fetch ใน frontend ผ่านอันนี้
- [ ] [`initAuth`](../../legacy-frontend/landing.js#L449) — auth bootstrap

---

# 📊 สถิติสรุป

| กลุ่ม | Functions | สถานะ refactor |
|---|---|---|
| 1. Auth + Login | 32 | 🟢 เพิ่ง fix v9.4.9 |
| 2. Upload + Queue | 39 | 🟡 hotspot — มี upload_files 180 lines |
| 3. Extraction + AI Ingest | 38 | 🟢 stable v9.4.2+ |
| 4. Files + Organize | 50 | 🟢 stable |
| 5. Knowledge Graph + Search | 35 | 🟢 stable |
| 6. Context Packs + Share | 38 | 🟢 stable |
| 7. Storage Router | 56 | 🟡 BYOS data-loss risk |
| 8. LINE Bot | 50 | 🟢 stable |
| 9. MCP Server | 41 | 🟡 mcp_streamable_http 136 lines |
| 10. Profile + Personality | 32 | 🟢 stable |
| 11. Billing + Plan Limits | 45 | 🟢 stable |
| 12. Admin + Misc + Infra | 60 | 🟢 stable |
| 13. Frontend Misc | 30 | 🟢 stable |
| **รวม** | **~819** | **6/13 groups touched in v9.4.x** |

---

**สร้างโดย:** Claude Opus 4.7 (1M context) · session 2026-05-14
**Source data:** AST parse + regex (backend/ + legacy-frontend/)
**Re-generate:** `python -c "import ast; ..."` (ดู [docs/refactor/main-py-split-plan.md](../refactor/main-py-split-plan.md) สำหรับ AST trace command)
