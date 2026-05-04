# 🔬 Research: LINE vs Telegram vs Discord Bot สำหรับ PDB

**Author:** แดง (Daeng)
**Date:** 2026-05-02 (LINE+Telegram); updated 2026-05-02 (Discord)
**Question:** ความเป็นไปได้ของ chatbot 3 platform หลัก — upload, AI chat, ส่งไฟล์, query knowledge
**Status:** Research complete (3 platforms)

---

## 🎯 TL;DR (Executive Summary)

| มิติ | LINE | Telegram | Discord |
|---|---|---|---|
| **Thai market reach** | 🟢 56M (95% internet) | 🟡 few million (niche) | 🟡 dev/gamer/student (~5-10% LINE) |
| **Inbound file (user → bot)** | 🟢 ทุกประเภท ~100MB | 🟡 20MB cloud / 2GB self-host | 🔴 **10MB free** / 50MB Nitro Basic / 500MB Nitro |
| **Outbound file (bot → user)** | 🔴 PDF/DOCX **ไม่ได้** — ใช้ download link | 🟢 ทุกประเภท ≤50MB cloud / 2GB self-host | 🟢 **ทุกประเภท** ตาม channel boost / DM ตาม user Nitro |
| **AI text Q&A length** | 🟢 5,000 chars/msg | 🟡 4,096 chars/msg | 🔴 **2,000 chars/msg** (4k for users only — bots stuck at 2k) |
| **Rich UI** | 🟢 Flex Messages (custom JSON layout) | 🟡 Inline keyboard | 🟢 **Modals + buttons + select + embeds + ephemeral** (richest) |
| **Markdown** | 🔴 plain text only | 🟢 MarkdownV2 / HTML | 🟢 Discord-flavored markdown |
| **Cost** | 🟢 Free Communication plan + reply ฟรี | 🟢 100% Free | 🟢 100% Free API |
| **Setup** | M (Channel + verify) | S (BotFather + token) | S (Dev Portal + token + invite) |
| **Account linking** | OAuth + Account Link feature | Deep link `?start=<token>` | OAuth2 (cleanest) |
| **Webhook security** | 🟢 HMAC-SHA256 | 🟡 secret token header | 🟢 ed25519 signature |
| **Attachment URL persistence** | 🟢 ~14 วัน | 🟢 1 hour but refreshable | 🔴 **CDN URL expires ~24h + signed params** |
| **Proactive notifications** | Push 200/month free | unlimited (with rate limit) | 🟡 ต้อง shared server หรือ user-install |
| **Effort to MVP** | ~1.5-2 sprint | ~1-2 sprint | ~3-5 days (Pycord) |

### 🏆 Winners by use case
- **มวลชนไทยทั่วไป (consumer/SMB):** 🟢 **LINE** ขาดลอย
- **Power users / file size สำคัญ / formatting ดี:** 🟢 **Telegram**
- **Dev/student/gamer + UI สวย + DM ส่วนตัว:** 🟢 **Discord** (ผ่าน user-installable apps 2024+)

---

## 📋 LINE Bot — รายละเอียด

### ✅ Quick Verdict
- **Viable for chat + image/voice Q&A** but **bot CANNOT send PDF/DOCX back to user** — must use download link workaround
- **Inbound file ingestion works well**: PDF/DOCX/etc. arrive as `file` message, retrievable via `getMessageContent`
- **MVP cost ≈ free**: Communication plan = 0 THB, reply API ไม่นับ quota

### A. File Upload (user → bot → PDB)
- รับได้: `text`, `image`, `video`, `audio`, **`file`** (ทุกประเภท), `location`, `sticker`
- Max size: ไม่ publish exact — practical ~100MB safe (consumer LINE app cap = 1GB)
- PDF/DOCX/XLSX/ZIP → ทุกอย่างมาเป็น `file` message พร้อม `messageId`, `fileName`, `fileSize`
- Backend download: `GET https://api-data.line.me/v2/bot/message/{messageId}/content` + Bearer token
- Retention: ~14 วัน (ไม่ guarantee) → **download ทันทีเมื่อ webhook มา**

### B. AI Chat / Bidirectional
- Free-form text Q&A — bot reply max **5,000 chars/msg**
- Rich messages: **Flex Messages** (JSON custom layout), **Template** (Buttons/Confirm/Carousel), **Quick Reply**
- Multi-turn: server-side state keyed by `userId` + Postback actions
- Loading indicator: `POST https://api.line.me/v2/bot/chat/loading/start` (5-60 sec, 1:1 chat only)
- Reply token expires ~30 sec → ack 200 ทันที + reply async

### C. Knowledge Queries (text out)
- 5,000 chars/msg ≈ 500-word summary ใส่ได้สบาย
- ส่งได้ **5 message objects/call** (header + body + Quick Reply พร้อมกัน)
- URLs auto-linkify, URI Action ใน template = explicit button
- ❌ **Plain text only** — ไม่มี markdown/bold/code block (workaround: render PNG หรือใช้ Flex)

### D. File Download (bot → user) — 🔴 CRITICAL LIMIT
- ❌ **ไม่สามารถส่ง PDF/DOCX/XLSX/ZIP กลับได้**
- ส่งได้เฉพาะ: text, sticker, image (jpg/png), video (mp4), audio (m4a), location, imagemap, template, flex
- **Workaround universal pattern:** ส่ง Flex Message + URI button → link ไป signed download URL บน PDB backend → user tap → เปิดใน LINE in-app browser หรือ download

### E. Forwarding & Sharing
- ✅ Forward message มาเป็น fresh event ของ underlying type — bot ได้รับ file content ผ่าน `getMessageContent`
- หลายไฟล์: แต่ละไฟล์ = webhook event แยก (correlate ด้วย `userId` + arrival window)
- Bot ส่งไป group/friend อื่นไม่ได้ — ต้อง add bot เข้า group นั้น

### F. Account Linking
- **Account Link feature:** issue `linkToken` → redirect `https://access.line.me/dialog/bot/accountLink?linkToken=...&nonce=...` → ได้ `accountLink` webhook กลับ
- LINE Login = แยก channel (OAuth 2.1 + OIDC) — pattern ปกติคือ web sign up ผ่าน LINE Login + เชื่อม bot ตอน first interaction
- 1 PDB user → multi LINE accounts ได้ (DB schema ตัดสิน)

### G. Cost (Thailand 2026)
- 3 plans: **Communication (free)**, Light, Standard
- Free tier: ~200 push msgs/month
- **Inbound user→bot = ฟรี ไม่จำกัด**
- **Reply API = ฟรี ไม่นับ quota** ⭐ (huge for Q&A bot)
- เฉพาะ Push/Multicast/Broadcast/Narrowcast นับ quota
- ราคา Light/Standard ~1,200/1,500 THB/เดือน (verify ใน OA Manager)

### H. Implementation
- Setup ~30 นาที: Provider → Messaging API channel → token → webhook (HTTPS + valid TLS, **no self-signed**)
- SDK: **`line-bot-sdk-python`** (official, maintained)
- Webhook security: `X-Line-Signature` = HMAC-SHA256(channel secret, raw body), base64
- Fly.io SIN works fine (LINE infra Tokyo/Singapore, latency 40-60ms)

### I. Thai Market
- 56M+ LINE users (>80% population)
- Success: Wongnai, SCB EASY, KBank, True Money, Lazada, LINE MAN
- Knowledge mgmt space underserved — PDB เป็น differentiated entrant
- Thai UX expectations:
  - **Rich Menu always-on** ที่ bottom (6-tile grid)
  - Thai Quick Replies ทุก turn
  - Emoji-friendly tone
  - Image-heavy responses > wall of text
  - Instant <3 sec response (use loading animation)

### J. Dealbreakers
1. **ส่งไฟล์กลับไม่ได้** (PDF/DOCX) — ต้องใช้ download link
2. **No markdown** in text
3. Push messages ไป non-friends ไม่ได้ — user ต้อง add bot เป็นเพื่อนก่อน
4. >30 sec async reply ใช้ Push (นับ quota)
5. **LINE Notify ปิดตัว April 2025** — ห้าม build บนนี้
6. **Avoid:** Buttons/Confirm/Carousel template (legacy) → ใช้ **Flex Messages** แทน

---

## 📋 Telegram Bot — รายละเอียด

### ✅ Quick Verdict
- **YES — technically excellent fit**: mature, free, generous limits, supports any file type, rich formatting, deep-link account binding
- **Biggest limitation = Thai market reach** (~5-10% vs LINE 95%)
- **MVP: 1-2 weeks**, free API, free BotFather

### A. File Upload (user → bot → PDB)
- ทุกประเภท: photo/video/audio/document/voice (OGG/Opus)/video_note/sticker/animation/location/contact/poll
- ⚠️ **Max 20 MB/file via cloud Bot API** — users upload Telegram ได้ 2GB แต่ bot's `getFile` limit = 20MB
- Self-hosted Bot API server lifts to 2GB (extra ops)
- PDF/DOCX/XLSX/ZIP → ทุกประเภทเป็น `document`, no MIME restriction
- Download flow: extract `file_id` → `getFile?file_id=...` → `file_path` (valid ≥1 hour) → GET `https://api.telegram.org/file/bot<TOKEN>/<file_path>`

### B. AI Chat / Bidirectional
- Free-form text Q&A — **4096 UTF-16 chars/msg**
- Rich UI: `inline_keyboard` (callback), `reply_keyboard`, `force_reply`, **inline mode** (@bot ใน chat อื่น)
- No built-in state — store ใน DB/Redis (aiogram + python-telegram-bot มี FSM helper)
- Typing indicator: `sendChatAction` (typing/upload_document/etc.) — show ~5 sec
- Webhook timeout ~60 sec — best practice ack 200 + async work

### C. Knowledge Queries
- 4096 chars/msg, captions 1024 chars
- Send unlimited messages sequentially (rate limit 1/sec/chat)
- Clickable links auto-detected + `inline_keyboard` (callback ≤64 byte payload หรือ url button หรือ web_app button → Telegram Mini App)
- **3 parse modes:** MarkdownV2 (strict escape), **HTML** (recommended — `<b>`, `<i>`, `<u>`, `<code>`, `<pre>`, `<a>`, `<blockquote>`, `<tg-spoiler>`), legacy Markdown

### D. File Download (bot → user) — ✅ ไม่จำกัดประเภท
- ✅ **ส่งไฟล์ทุกประเภทกลับได้**: PDF, DOCX, XLSX, MP3, MP4, ZIP, EXE — no MIME blocklist
- Limits (cloud Bot API):
  - sendPhoto: 10 MB
  - **sendDocument / sendVideo / sendAudio: 50 MB**
  - Self-hosted Bot API: **2 GB**
- API: `sendDocument` (generic), `sendAudio` (MP3/M4A + player), `sendVoice` (OGG bubble), `sendVideo` (MP4 inline player)

### E. Forwarding & Sharing
- ✅ Forward จากที่ไหนก็ได้ → bot ได้รับ full Message + `forward_origin` metadata + original `file_id`
- **Media groups (album):** up to 10 photos/videos ใน 1 `sendMediaGroup` (รับเป็น `media_group_id` เดียวกัน)
- Sharing back: `t.me/<botname>?start=<token>` deep links + `switch_inline_query` button (user เลือก chat ส่ง)

### F. Account Linking
- **Deep link with start parameter:** PDB web → show `t.me/PDBBot?start=<token>` → user tap → bot รับ `/start <token>` → bind
- **Telegram Login Widget** บน web (HMAC-signed payload — verify ด้วย bot token) → solid SSO
- 1 PDB user → multi Telegram accounts (DB ตัดสิน)

### G. Cost & Limits
- **100% free, no commercial restrictions**, no paid tier
- Soft limits: ~30 msg/sec global, **1 msg/sec per chat**, ~20 msg/min per group
- Bursts ok, sustained over → 429 + `retry_after`
- No subscriber cap, bots serve millions

### H. Implementation
- Setup <30 นาที: BotFather → /newbot → token → webhook (HTTPS + Let's Encrypt fine)
- **SDK recommendation: aiogram 3.x** (async-first, FastAPI-friendly, FSM, modern type hints) — perfect fit PDB stack
- Alternative: python-telegram-bot 21+ (more popular but verbose)
- Webhook security: `setWebhook` accepts `secret_token` → Telegram sends in `X-Telegram-Bot-Api-Secret-Token` header (ไม่ใช่ HMAC แต่ enough)
- Fly.io SIN works fine — Telegram global, **not blocked in Thailand**

### I. Thai Market Reality
- ⚠️ **Telegram = niche in Thailand** — LINE dominates ~50M+ TH MAU (~95%)
- Telegram TH: low single-digit millions — concentrated in **crypto/Web3, IT/devs, expats, traders, privacy-conscious users**
- For mainstream Thai knowledge workers: LINE = default
- Few mainstream Thai bot success stories (strong in crypto signal bots)

### J. Dealbreakers
1. **20 MB inbound cap** on cloud Bot API → big files need self-hosted
2. **No native rich UI** like LINE Flex — only buttons/text/media
3. **No business verification** like LINE OA — bots feel "indie" to TH users
4. **Thai market reach small** — most PDB targets won't have Telegram
5. **No payments rail in TH** (Telegram Stars exist but PromptPay/TrueMoney = LINE territory)

### K. vs LINE Beats
- ✅ File size (50MB doc vs LINE workaround), any file type freely
- ✅ Free at scale (LINE charges per msg above free)
- ✅ Inline keyboards + callback queries
- ✅ MarkdownV2/HTML formatting
- ✅ Mature Python SDKs
- ✅ Deep linking simpler

### L. LINE Beats Telegram
- ✅ **Thai market reach 10-20× larger**
- ✅ LINE Pay / Rabbit LINE Pay payments
- ✅ Flex Message rich card UI
- ✅ LIFF (full webview app inside LINE)
- ✅ LINE Login = de-facto Thai SSO
- ✅ Brand trust (verified Official Account)

---

## 🎯 ตอบคำถามเฉพาะของ user (10 ข้อ)

| # | คำถาม | LINE | Telegram |
|---|---|---|---|
| 1 | **อัพโหลดไฟล์เข้า bot** | ✅ ทุกประเภท ~100MB | ✅ ทุกประเภท แต่ 20MB cloud / 2GB self-hosted |
| 2 | **AI chatbot ถามตอบทั่วไป** | ✅ 5,000 chars/msg | ✅ 4,096 chars/msg |
| 3 | **เหมือนคุยกับ AI chat บอท** | ✅ multi-turn + state ใน DB | ✅ multi-turn + state ใน DB |
| 4 | **คุยเรื่องข้อมูลไฟล์ได้** | ✅ — call PDB API ปกติ | ✅ — เหมือนกัน |
| 5 | **ถามจำนวนไฟล์** | ✅ — query DB → ตอบ "คุณมี 47 ไฟล์" | ✅ — เหมือนกัน |
| 6 | **ถามไฟล์ที่เกี่ยวข้องมีอะไรบ้าง** | ✅ — call retriever.py + ส่ง Flex card list | ✅ — call retriever.py + ส่ง inline keyboard list |
| 7 | **จัด context pack ได้** | ✅ — Quick Reply เลือกไฟล์ + button "Create Pack" | ✅ — inline keyboard + callback |
| 8 | **ส่งต่อไฟล์ได้ง่าย (forward)** | ✅ user forward → bot ได้ file content | ✅ — เหมือนกัน |
| 9 | **ขอไฟล์ผ่าน bot ให้ส่งกลับมา** | ❌ **ไม่ได้** ส่ง PDF กลับ → ต้องใช้ download link | ✅ **ส่งได้** ทุกประเภท ≤50MB |
| 10 | **ส่งให้คนอื่นต่อง่าย** | ✅ user share download link ผ่าน LINE | ✅ user forward Telegram message |

---

## 🏆 Recommendation สำหรับ PDB

### Strategy: **LINE Bot first (Phase 1) → Telegram Bot ทีหลัง (Phase 2 ถ้าจำเป็น)**

**Reasoning:**
1. **Thai market dominance** — 95% of target users มี LINE อยู่แล้ว
2. **File send back limitation** ของ LINE = แก้ได้ด้วย download link pattern (Thai users คุ้นเคยกับ flow นี้แล้ว — SCB Easy, KBank ใช้)
3. **Telegram** เก็บไว้ Phase 2 สำหรับ niche segment (developer/crypto/expat) ถ้า demand มา

### LINE Bot MVP Scope (Phase 1 — v7.5.0 หรือ v8.0.0)

**สิ่งที่ทำได้ครอบคลุม 95% ความต้องการ:**

| Feature | Implementation |
|---|---|
| Account linking | LINE Login + Account Link feature (linkToken + nonce) |
| Upload file ใส่ PDB | User send file → webhook → `getMessageContent` → save → extract → organize |
| AI chat | Free-form text → call PDB `/api/chat` → ตอบ 5000 chars + Quick Reply |
| Query file count | "/stats" หรือ Rich Menu button → ตอบ "คุณมี N ไฟล์, M collections" |
| Search related files | "หาไฟล์เกี่ยวกับ AI" → call `vector_search.hybrid_search()` → Flex card list |
| Get file back | "ขอไฟล์ X" → ตอบ Flex card + URI button → tap → in-app browser open download URL ของ PDB |
| Create context pack | Multi-turn flow ผ่าน Quick Reply: "เลือกไฟล์ → ตั้งชื่อ → confirm" |
| Forward file | User forward PDF → bot ingest อัตโนมัติ |
| Notify summary | Push message หลัง organize เสร็จ (count against 200/month — ใช้แค่ critical event) |

**Rich Menu (always-on):**
```
┌───────────┬───────────┬───────────┐
│ 📤 อัพโหลด │ 🔍 ค้นหา  │ 💬 ถาม AI │
├───────────┼───────────┼───────────┤
│ 📚 คอลเลค │ ⚙️ ตั้งค่า │ 🌐 เปิดเว็บ│
└───────────┴───────────┴───────────┘
```

**Effort estimate:** 1.5-2 sprint (2-3 สัปดาห์) for solo dev
- Sprint 1: Webhook + Account Link + file upload + basic chat
- Sprint 2: Rich Menu + Flex cards + context pack flow + download links

**Tech stack additions:**
- `line-bot-sdk-python` (official)
- New backend module: `backend/line_bot.py`
- New endpoint: `POST /webhook/line`
- New table: `line_users` (line_user_id ↔ pdb user_id mapping)
- New env vars: `LINE_CHANNEL_SECRET`, `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_LOGIN_CHANNEL_ID`

---

---

## 📋 Discord Bot — รายละเอียด

### ✅ Quick Verdict
- **Strong YES technically** — richest interaction primitives ของทุก platform (modals, buttons, select menus, embeds, slash commands, threads, ephemeral replies)
- **Biggest limitation:** 10 MB user upload (free), 2,000 chars bot message cap (Nitro 4k ไม่ครอบคลุม bot), CDN attachment URLs **expire ~24h** ต้อง download ทันที
- **MVP cost/effort:** Free API, ~3-5 days ship Pycord on Fly.io. **Tertiary after LINE+Telegram for Thai market**

### A. File Upload (user → bot → PDB)
- **Any file type** ใน DM และ channels — no MIME restriction
- Free tier: **10 MB** (cut from 25 MB ใน Sept 2024 ✋ recent change)
- Nitro Basic ($2.99): 50 MB. Nitro ($9.99): 500 MB
- Boosted server: L1 = 10 MB, L2 = 50 MB, L3 = 100 MB
- Download: `attachment.url` หรือ `attachment.proxy_url` → `await attachment.read()` (Pycord)
- **🔴 Attachments expire** — Dec 2023 onward URLs มี `?ex=&is=&hm=` signed params, 404 หลัง ~24h → **ต้อง download ทันทีบน webhook**, ห้าม cache URL

### B. AI Chat / Bidirectional
- Free-form text ใน DM/server — user input 2,000 chars (4,000 with Nitro)
- **Embeds:** max 10/msg, 6,000 chars total (title 256, description 4,096, 25 fields)
- **Components:** buttons (5/ActionRow × 5 rows), select menus, **modals** (5 text inputs + recent file upload component)
- **Polls** GA 2024
- **Slash commands** + autocomplete (≤25 choices in <3s)
- **Modals** = popup forms 5 inputs — perfect for "Create context pack" flow
- Threads (public/private) + forum channels — organized convos
- Typing: `async with channel.typing(): ...`
- Slash command: **3 sec ack** → defer → **15 min** to followup via webhook (long LLM/RAG fits)

### C. Knowledge Queries
- **Bot text cap: 2,000 chars hard** ⚠️ (Nitro 4k extension does NOT apply to bots — confirmed intentional)
- Multi messages allowed (rate limit ~5/5s per channel, global 50/s)
- **Discord-flavored markdown:** bold, italic, `code`, ```code blocks``` with lang, > quotes, lists, # headers (2023), spoilers `||`, masked links `[text](url)`, ANSI colors
- Embeds = ideal for file/search results: title + URL + description + thumbnail + fields + color stripe + footer + timestamp

### D. File Download (bot → user)
- ✅ **ทุกประเภท:** PDF, DOCX, audio, video, ZIP, exe (Discord ไม่ filter — client warns user)
- Bot send size = **channel's effective limit** (server boost level), DM = **user's tier** governs
- ใน DM ของ Nitro user = bot ส่งได้ถึง 500 MB
- Up to **10 attachments/msg**
- **Ephemeral replies** (`ephemeral=True`) — เห็นแค่ invoker, perfect for sensitive data ใน public channel (works only for interaction responses)

### E. Forwarding & Sharing
- ✅ **Native Forward feature** (late 2024) — user forward → bot DM (รวม attachments)
- Bot รับ `MessageReference` เมื่อ user reply + tag → pull via `message.reference.resolved` (needs Message Content intent — privileged for verified bots)
- Bot post embeds ที่ไหนก็ได้ที่มี permission

### F. Account Linking
- 3 patterns:
  - **(a) OAuth2 with `identify` scope** — redirect → discord.com/oauth2/authorize → get Discord user ID (cleanest)
  - **(b) `/link <token>` slash command** — token จาก PDB web → run `/link` ใน bot DM
  - (c) Deep link with `state` param
- With `identify + email` scopes → Discord ID + username + avatar + verified email → SSO into PDB web

### G. DM vs Server (CRITICAL for PDB privacy)
- DM = right channel for personal data
- ⚠️ Bot **cannot DM user unless they share at least one server** (default Discord rule)
- **🆕 Solution: User-installable apps (IntegrationType USER, 2024)** → user installs bot to account → slash commands work in any DM/channel **without shared server**. **This is the modern PDB pattern**
- Slash commands in DMs: `dm_permission=True` หรือ IntegrationType USER
- Proactive DMs: `user.send()` only if shared-server-or-installed
- **Aggressive flags for mass-DM** — batch + stagger, ห้าม spam (TOS violation = bot ban)

### H. Cost & Limits
- **API ฟรี 100%, no paid tier**
- Global: **50 req/sec per bot**
- Per-route: ~5/5s per channel for sends
- 100 global slash commands per app, 100 per guild, 25 subcommands, 25 options
- **100-server cap until bot verification** (Stripe identity check) — also required for Message Content intent

### I. Implementation
- Setup: Dev Portal → Application → Bot → token → OAuth2 URL Generator → invite. ~10 min
- **Best Python SDK 2026: Pycord** (cleaner slash API, ships features same-day, FastAPI-friendly via background asyncio task)
- discord.py = back in active maintenance, most popular
- **Gateway (WebSocket)** required for messages/typing/member events
- **HTTP-only interaction webhooks** work for slash-command-only bots (serverless-friendly)
- For PDB: ใช้ทั้ง 2 — gateway สำหรับ DMs, interactions สำหรับ slash commands
- **Fly.io SIN works fine** — set `auto_stop_machines = false`, `min_machines_running = 1`, `restart_policy = "always"`. ~$2/mo on shared-cpu-1x 256MB. Latency to Tokyo POP ~70ms

### J. Thai Market Reality
- **Discord = niche in Thailand** — heavy ใน gaming (Valorant, Genshin, RoV), anime, K-pop, dev/crypto
- ไม่ publish Thailand MAU แต่ third-party trackers ต่ำกว่า LINE 50M และต่ำกว่า Messenger
- **Thai professional knowledge workers ไม่อยู่บน Discord** — LINE สำหรับทุกอย่าง personal/professional, Teams/Google Chat สำหรับงาน
- Discord = teenage-30s gamer/creator/dev demographic
- Notable Thai usage: university servers (Chula, KMUTT, KMITL), gaming clans, NFT/crypto communities, Vtuber fan servers, Thai dev community (2bit.dev, ThaiProgrammer)
- Addressable Thai audience = "indie devs + gamers + students" → ~5-10% LINE reach

### K. Dealbreakers + Recent Changes
- **Dealbreakers:**
  1. **2,000-char bot message cap** — chunking ยาว RAG answers (workaround = embeds 4k char descriptions)
  2. **10 MB upload free tier** — many PDFs/scans/recordings exceed
  3. **CDN URL expires** — must download immediately
  4. **Cannot proactively DM** without shared server → "PDB Hub" server หรือ user-install
  5. **No native search** of bot's own messages by user (unlike Telegram)
- **Recent breaking changes:**
  - Sept 2024: free upload 25 MB → 10 MB
  - Dec 2023: CDN URLs signed + expiring
  - 2024: User-installable apps → enables DM bots without shared server (use this!)
  - Nov 2024: legacy bot tokens fully invalidated
  - Aug 2025 / Feb 2026: PIN_MESSAGES permission split out
  - Oct 2025: Components V2 — richer message layouts

### L. vs LINE + Telegram
- **Discord WINS:** rich interactive UI (modals, buttons, select menus, ephemeral, embeds), slash command + autocomplete, threads, free unlimited inbound text, dev-friendly OAuth2, polls
- **Discord LOSES:** file size (Telegram 2GB free, LINE ~100MB; Discord 10MB free), Thai user reach (LINE = #1 messenger), proactive notifications (Telegram zero friction; Discord needs shared-server/install), bot message length (Telegram 4096, LINE 5000, Discord 2000), attachment persistence (Telegram URLs persist; Discord expires)

---

## 📌 Sources

### LINE
- [Messaging API reference](https://developers.line.biz/en/reference/messaging-api/)
- [Sending messages](https://developers.line.biz/en/docs/messaging-api/sending-messages/)
- [Message types](https://developers.line.biz/en/docs/messaging-api/message-types/)
- [Pricing](https://developers.line.biz/en/docs/messaging-api/pricing/)
- [Account linking](https://developers.line.biz/en/docs/messaging-api/linking-accounts/)
- [Loading animation](https://developers.line.biz/en/docs/messaging-api/use-loading-indicator/)
- [Rich menus](https://developers.line.biz/en/docs/messaging-api/using-rich-menus/)
- [line-bot-sdk-python](https://github.com/line/line-bot-sdk-python)

### Telegram
- [Bot API](https://core.telegram.org/bots/api)
- [Bot features](https://core.telegram.org/bots/features)
- [Local Bot API server](https://core.telegram.org/bots/api#using-a-local-bot-api-server)
- [Login Widget](https://core.telegram.org/widgets/login)
- [aiogram 3](https://docs.aiogram.dev/)

### Discord
- [Discord Developers Intro](https://discord.com/developers/docs/intro)
- [File Attachments FAQ](https://support.discord.com/hc/en-us/articles/25444343291031-File-Attachments-FAQ)
- [Server Boosting FAQ](https://support.discord.com/hc/en-us/articles/360028038352-Server-Boosting-FAQ)
- [Rate Limits](https://docs.discord.com/developers/topics/rate-limits)
- [Change Log (recent)](https://discord.com/developers/docs/change-log)
- [Pycord docs](https://docs.pycord.dev/)
- [discord.py](https://discordpy.readthedocs.io/)
