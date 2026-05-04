# 🔬 Research: MCP File Upload — Deep Dive

**Author:** แดง (Daeng) — synthesized จาก 3 parallel subagent research runs
**Date:** 2026-05-02
**Question:** AI ตัวอื่น (Claude/ChatGPT/Antigravity) จะอัพโหลดไฟล์ binary เข้า PDB ผ่าน MCP ได้ยังไง?
**Status:** Research complete → ready for plan design

---

## 🎯 TL;DR (3 บรรทัด)

1. **MCP spec ปัจจุบัน (2025-11-25) ไม่มี first-class binary upload primitive** — มีแต่ base64-in-string ผ่าน `tools/call` arguments เท่านั้น
2. **Claude ส่งไฟล์ผ่าน MCP tool param ตรงๆ ไม่ได้ในทางปฏิบัติ** — Claude เห็นแต่ extracted text (PDF/DOCX) หรือ image pixels (รูปภาพ) ไม่ได้ส่ง raw bytes ของไฟล์อัตโนมัติ + token budget เป็นเพดานจริง (~150KB image = ~50K tokens)
3. **Industry pattern ชนะ:** **base64-inline tool** (สำหรับไฟล์ < 5-10 MB) **+ presigned URL tool** (สำหรับไฟล์ใหญ่) — ใช้โดย S3 MCP, Supabase Storage MCP, Notion MCP

---

## 1️⃣ MCP Spec — Protocol-level Findings

**Verdict:** Native binary in MCP today: **Limited** — base64-encoding inside JSON-RPC content blocks เป็น mechanism เดียวที่ spec รองรับ; ไม่มี first-class file-upload primitive ทั้งสองทิศทาง

### Capability Matrix

| Primitive | Direction | Binary support | ใช้ได้กับ PDB upload? |
|---|---|---|---|
| `tools/call` arguments | client → server | ไม่มี native — base64-in-string param เท่านั้น | ✅ ทางเดียวที่ spec อนุญาต |
| `tools/call` result `content[]` | server → client | ✅ image/audio/resource (base64 + mimeType) | ❌ ผิดทิศทาง |
| Resources (`resources/read`) | server → client only | ✅ blob base64 + mimeType | ❌ ไม่มี `resources/write` |
| Resource templates / subscribe | server → client | เหมือน Resources | ❌ |
| Sampling | client → server | image/audio | ❌ ไว้ขอ host รัน LLM ไม่ใช่ ingest |
| Roots | client → server | URI hint อย่างเดียว | ❌ ไม่มี payload |
| Elicitation (2025-06-18 ใหม่) | server → client | text-only schema | ❌ |
| Streamable HTTP transport | bidirectional | JSON-RPC over POST/SSE — **ไม่มี binary frame, ไม่มี chunked upload primitive** | แค่ carrier, ไม่ช่วย chunk |

### Spec Evidence (ที่ verify แล้ว)

- **Latest spec:** 2025-11-25 (schema `schema/2025-11-25/schema.ts`); previous stable 2025-06-18
- **Resources = server→client only** — มีแค่ `resources/list`, `resources/templates/list`, `resources/read`, `resources/subscribe`. **ไม่มี** `resources/write` / `resources/create` / `resources/upload`
- **Tool inputs = JSON Schema only** — `inputSchema` ไม่มี image/audio/blob input content type (มีแค่ใน Tool Result)
- **Streamable HTTP** — "JSON-RPC messages MUST be UTF-8 encoded" → no binary frames, no multipart, no byte-range resume
- **No large-payload spec** — ไม่มี section ไหนใน spec กำหนด chunked transmission สำหรับ tool args

### Sources
- [MCP Specification 2025-11-25](https://modelcontextprotocol.io/specification)
- [MCP Resources concept](https://modelcontextprotocol.io/docs/concepts/resources)
- [MCP Tools concept](https://modelcontextprotocol.io/docs/concepts/tools)
- [MCP Transports 2025-06-18](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)

---

## 2️⃣ Claude/AI Client Behavior — Reality Check

### Q1: Claude ส่ง binary bytes ของไฟล์ที่ user แนบในแชทผ่าน MCP tool ได้ไหม?
**A:** ❌ **ไม่ได้แบบ realistic** — Claude เห็นแค่ **extracted text** (PDF/DOCX) หรือ **image pixels** (รูปภาพผ่าน vision) ไม่ได้เห็น raw bytes ของไฟล์ Claude ทำ base64 encode bytes แล้วส่งเข้า MCP tool ได้ในทางทฤษฎี แต่ไม่ใช่ pattern ที่ตั้งใจ + เปลือง token มหาศาล (image 150KB = base64 200KB ≈ 50K+ tokens)

### Q2: Anthropic Files API integrate กับ MCP ไหม?
**A:** ❌ **ไม่มี published integration** — Files API (beta 2025) เป็น feature แยก สำหรับ Anthropic API call โดยตรง (upload → file_id → reference ใน Messages API). MCP server ไม่มี access กับ file_id หรือ Files API

### Q3: Practical input token limit สำหรับ base64 blob?
**A:** ❌ **ไม่ viable** — 5MB base64 (~6.7M chars ≈ 1.7M tokens) เกิน context Claude Sonnet 4.5/4.6 (200K-1M tokens). Even ภาพ 150KB (50K tokens) ก็หนัก. Recommended pattern จาก Anthropic = ส่ง **path หรือ URL reference**

### Q4: Tool param size limit?
**A:** **Unclear from public docs** — Claude Code มี output limit (10K warning, 25K cap, configurable via `MAX_MCP_OUTPUT_TOKENS`) แต่**ไม่มี published input parameter size limit**. Tool schema ใส่ `maxLength` constraint ได้ แต่ไม่มี enforced cap จาก Anthropic

### Q5: ChatGPT / Antigravity behavior?
**A:** **Unclear from public docs** — OpenAI เพิ่ม MCP support 2025 แต่ไม่มี public comparison ระหว่าง clients. Antigravity (Claude wrapper) น่าจะตาม Claude pattern แต่ docs ไม่ระบุ

### Q6: Anthropic recommended pattern?
**A:** ✅ **ส่ง path หรือ file_id reference, ไม่ใช่ binary content** — reference servers (filesystem, GitHub) ใช้ tool ที่ return file paths/URLs ไม่ใช่ base64 blobs. MCP designed for **tool I/O by reference** — server read/write โดยตรง ไม่ใช่ Claude upload binary payload

### Sources
- [Files API Documentation](https://platform.claude.com/docs/en/build-with-claude/files)
- [Claude Agent SDK MCP](https://code.claude.com/docs/en/agent-sdk/mcp)
- [Uploading files to Claude Help Center](https://support.claude.com/en/articles/8241126-upload-files-to-claude)
- [Files and Resources with MCP - LLMindset](https://llmindset.co.uk/posts/2025/01/mcp-files-resources-part1/)

---

## 3️⃣ Industry Patterns — How Real MCP Servers Do It

### Server Survey (6 servers)

| # | Server | Repo | Tool name | Pattern | Max size | Note |
|---|---|---|---|---|---|---|
| 1 | Anthropic Filesystem | `modelcontextprotocol/servers/filesystem` | `write_file(path, content)` (text) / `read_media_file(path)` (returns base64+mime) | Local file path | N/A | **No `write_media_file`** — binary write intentionally out of scope |
| 2 | Anthropic GitHub (archived) | `servers-archived/github` | `create_or_update_file(owner, repo, path, content, message, branch, sha?)` + `push_files` | Inline UTF-8 string content (server base64s before PUT) | GitHub API limits | **Effectively text-only** — no binary input path |
| 3 | Anthropic Google Drive (archived) | `servers-archived/gdrive` | none — exposes via Resources `gdrive:///<fileId>` | Resource URI + ReadResource | N/A | **Pure read-only**, no upload tool. Demonstrates resource-URI pattern |
| 4 | **txn2/mcp-s3** (Go, production) | `txn2/mcp-s3` | `s3_put_object(bucket, key, content, is_base64, content_type, metadata)` + `s3_presign_url` | **Dual-mode inline content** + presigned URL sidecar | `MaxPutSize` default 100MB | **Closest to PDB use case** — base64 flag + presigned URL escape hatch |
| 5 | Desmond-Labs/supabase-storage-mcp | `Desmond-Labs/supabase-storage-mcp` | `upload_image_batch(files: [{path \| base64_content, filename, mime_type}])` | **Batched dual-mode** (path OR base64 data-URI per item) | 50MB/file, 500 files/batch | "Claude Desktop compatible". 3 parallel streams |
| 6 | goonoo/mcp_notion_upload (Python FastMCP) | `goonoo/mcp_notion_upload` | `upload_file_to_notion(file_path)` + `upload_and_attach_file_to_page(file_path, page_id)` | **Local file path only** — server reads bytes + proxies through Notion 3-step API | 20MB hard cap (Notion limit) | Returns Notion `file_upload_id` reusable across blocks |

### Patterns Observed

**Pattern A — Base64 inline string in tool args**
- Used by: txn2/mcp-s3 (`is_base64` flag), Supabase Storage MCP (data-URI option)
- Pros: Universal fallback, simplest schema
- Cons: bounded by JSON/transport size + token budget

**Pattern B — UTF-8 text content inline (no binary)**
- Used by: filesystem `write_file`, GitHub `create_or_update_file`/`push_files`
- Pros: dominant when source-of-truth is text
- Cons: binary unsupported by design

**Pattern C — Local file path reference**
- Used by: Notion-upload, Supabase Storage (path mode), filesystem reads
- Pros: server reads bytes itself, no token cost
- Cons: **only works for stdio transport** (server + client share filesystem) — **breaks for hosted SaaS**

**Pattern D — MCP Resource URI pointing at storage**
- Used by: gdrive (`gdrive:///<id>`)
- Pros: spec-blessed for binaries; client decides when to materialize
- Cons: **only for exposing data, not for ingestion**

**Pattern E — Sidecar presigned URL (out-of-band)**
- Used by: txn2/mcp-s3 (`s3_presign_url`), Notion's underlying 3-step API
- Pros: bypass JSON-RPC text limit; uses plain HTTPS
- Cons: 2-step flow (request URL → upload → finalize)

### Verdict for PDB

**Pattern A (base64 inline) + Pattern E (presigned URL) = dominant managed-storage combo** — used by every production MCP server ที่จัดการ binary จริง (S3, Supabase, Notion).

Pattern C (local path) ใช้ไม่ได้ — PDB เป็น hosted SaaS, server กับ user filesystem ไม่ shared

### Sources
- [modelcontextprotocol/servers — filesystem](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem)
- [servers-archived/github](https://github.com/modelcontextprotocol/servers-archived/tree/main/src/github)
- [servers-archived/gdrive](https://github.com/modelcontextprotocol/servers-archived/tree/main/src/gdrive)
- [txn2/mcp-s3](https://github.com/txn2/mcp-s3)
- [Desmond-Labs/supabase-storage-mcp](https://github.com/Desmond-Labs/supabase-storage-mcp)
- [goonoo/mcp_notion_upload](https://github.com/goonoo/mcp_notion_upload)
- [makenotion/notion-mcp-server issue #191](https://github.com/makenotion/notion-mcp-server/issues/191)

---

## 4️⃣ Synthesized Recommendation for PDB

### Strategy: **3-tool combo (base64 + URL fetch + presigned URL)**

| Tool | Use case | File size | Trigger |
|---|---|---|---|
| `pdb_upload_text` (มีอยู่แล้ว — ขาด wiring) | AI generate text เอง | < 1 MB practical | Claude สร้าง markdown notes |
| 🆕 `pdb_upload_file` | AI มีไฟล์ (rare today, future-proofing) | ≤ 5 MB practical | Claude แนบรูป small image |
| 🆕 `pdb_upload_from_url` | User paste URL | ≤ 10 MB | "เก็บ paper จาก link นี้" — **most common** |
| 🆕 `pdb_request_upload_url` | ไฟล์ใหญ่ (Phase 2) | ≤ 100 MB | "เก็บ video bootcamp 50MB" |

### Why this combo (not single tool)

1. **Reality check จาก research:** Claude วันนี้ไม่ได้ส่ง binary bytes ไฟล์ที่ user แนบเข้า tool ตรงๆ — ส่งแต่ extracted text (Q1 ของ research 2). User scenario "อัพไฟล์เข้า Claude แล้วบอก save" → realistic flow คือ Claude **เห็น text** แล้วเรียก `upload_text` ส่ง text เข้า PDB → ไฟล์ binary ตัวจริงหายไป
2. **URL fetch = silver bullet for current reality** — ถ้า user upload ไฟล์เข้า Drive/Dropbox ก่อน แล้ว paste link → AI เรียก `upload_from_url` → server pull binary จริงเก็บได้
3. **Base64 = future-proof** — เมื่อ Claude/MCP spec รองรับ binary attachment passthrough ดีขึ้น tool พร้อมใช้
4. **Presigned URL = Phase 2** — ไฟล์ใหญ่กว่า 10MB (ของจริงไม่ค่อยเจอใน knowledge base personal)

### Storage routing (user vision: BYOS หรือ managed)

ทุก tool ใช้ logic เดียวกัน:
1. Decode/fetch → save bytes ไป `uploads/{file_id}_{filename}` (server volume)
2. `extract_text()` + `compute_content_hash()` + insert DB row
3. ถ้า `user.storage_mode == "byos"`:
   - `storage_router.push_raw_to_drive_if_byos()` → upload ไป `/Personal Data Bank/raw/`
   - server volume = cache (ลบหรือเก็บไว้ตาม policy)
4. ถ้า `"managed"`:
   - server volume = source of truth
5. (auto, default) → `run_organize` → cluster + summary + dedupe + graph

→ **ตรงตาม vision user 100%** — AI ไม่ต้องรู้ว่าเก็บที่ไหน user setting ตัดสินใจให้

### Phase scope (แนะนำ)

**Phase 1 (1 sprint, ~v7.5.0):**
- 🆕 `pdb_upload_from_url` — main tool ที่ user อยากได้
- 🔧 wire `pdb_upload_text` ที่มีอยู่ → `check_upload_allowed` + `compute_content_hash` + `push_raw_to_drive_if_byos` + auto-organize flag (อุด 4 gaps ที่บอกตอบที่แล้ว)
- 🛡️ SSRF defense module (block private IPs, force HTTPS, size cap, timeout)

**Phase 2 (later, ~v7.6.0):**
- 🆕 `pdb_upload_file` (base64) — เผื่อ MCP spec evolve
- 🆕 `pdb_request_upload_url` + `pdb_finalize_upload` — large file path

**Phase 3 (BYOS expansion):**
- 🆕 `pdb_import_from_drive(drive_file_id)` — สำหรับ BYOS users ที่ไฟล์อยู่ใน Drive ตัวเองอยู่แล้ว (reuse OAuth)

---

## 5️⃣ Risks / Open Questions ก่อนเขียน plan

| # | Question | Default ที่แดงแนะนำ |
|---|---|---|
| 1 | URL fetch — whitelist domains หรือ allow ทั้งหมด? | Allow ทั้งหมด + SSRF guard (block private IP/localhost) |
| 2 | URL fetch ไฟล์ Drive private ของ user เอง — ใช้ user's OAuth ไหม? | Phase 1: ไม่ — user ต้อง share "Anyone with link". Phase 2 (= `pdb_import_from_drive`) ค่อยใช้ OAuth |
| 3 | Auto-organize default = true? | ใช่ — UX ลื่น + ตรงตาม vision |
| 4 | Plan limit enforcement — เหมือน HTTP `/api/upload`? | ใช่ — `check_upload_allowed()` เดียวกัน |
| 5 | File size limit — เหมือน HTTP (10MB) หรือใหญ่กว่า? | เหมือน — 10MB (URL fetch ก็จำกัดเท่ากัน) |
| 6 | Duplicate detection — trigger ทันทีหลัง MCP upload หรือรอ organize? | รอ organize (เหมือน HTTP path — DUP-003 invariant) |
| 7 | Response shape — รวม `duplicates_found` ไหม? | ไม่ — organize-new จะส่งใน next call |
| 8 | MCP tool permission — default enabled หรือ disabled? | Default disabled (per security best practice — user เปิดใน MCP Setup) |

---

## 6️⃣ Decision Tree — เลือก Path ตาม User Intent

```
User บอก AI "เก็บไฟล์นี้ใน PDB"
         │
         ├── ไฟล์อยู่ที่ URL (Drive shared, web)?
         │   └── YES → AI เรียก pdb_upload_from_url(url) ✅
         │
         ├── ไฟล์เป็น text ที่ AI generate เอง?
         │   └── YES → AI เรียก pdb_upload_text(content) ✅
         │
         ├── ไฟล์อยู่ใน BYOS Drive ของ user (Phase 3)?
         │   └── YES → AI เรียก pdb_import_from_drive(drive_id) ✅
         │
         └── ไฟล์อยู่ใน Claude chat แต่ไม่มี URL?
             ├── ไฟล์เล็ก (text/small image)?
             │   └── AI extract text → pdb_upload_text ✅
             │   └── หรือ Phase 2: base64 → pdb_upload_file ✅
             │
             └── ไฟล์ใหญ่?
                 └── Phase 2: pdb_request_upload_url ✅
                 └── หรือ AI บอก user ให้ upload ที่ Drive ก่อนแล้วส่ง URL กลับมา
```

---

## ✅ Conclusion

**Vision ของ user ทำได้** — แต่ต้องรู้จริงว่า:
1. **MCP spec ปัจจุบันไม่มี first-class binary** — base64-in-string คือ official path เดียว
2. **Claude ไม่ส่ง binary bytes ไฟล์ที่ user แนบเข้า tool ตรงๆ** วันนี้
3. **URL fetch = realistic primary path** สำหรับ "เก็บไฟล์นี้" — user paste link → server pull
4. **3-tool combo** = strategic best-fit (text + URL + base64) — ครอบคลุม + future-proof
5. **Storage routing reuse `user.storage_mode`** = vision ตรงเป๊ะ

**Ready to plan v7.5.0** — รอ user ตอบ Q1-8 ใน section 5 (หรือบอก "ตามที่แนะนำ") → เขียน [plans/mcp-file-upload-v7.5.0.md](../plans/mcp-file-upload-v7.5.0.md) ได้ทันที
