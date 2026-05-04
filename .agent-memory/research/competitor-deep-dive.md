# 🔬 Competitor Deep Dive — PDB Position in Market

**Author:** แดง (Daeng)
**Date:** 2026-05-02
**Status:** Global research done; Thai market research in progress (background agent)
**Purpose:** Strategic positioning before committing to LINE bot or other channels

---

## 🎯 TL;DR — 5 ประโยคที่ user ต้องรู้

1. **NotebookLM (Google)** = existential threat ของ document Q&A — distribution ฟรี + Gemini quality
2. **Notion AI** = ครอง knowledge worker segment — ใครอยู่ Notion อยู่แล้วไม่ย้าย
3. **Mem.ai 2.0 relaunched 2026** ที่ $12/เดือน = closest "AI thought partner" overlap แต่**ไม่มี MCP/BYOS**
4. **Pieces.app** = MCP-native personal memory เท่านั้น แต่ **dev-only** — ไม่ใช่ general user
5. **ไม่มีคู่แข่งคนไหนรวม 4 pillar ของ PDB** (auto-organize + AI chat + MCP-out + BYOS-to-Drive) → **moat อยู่ที่ bundle ไม่ใช่ feature เดี่ยว**

---

## 📊 Tier 1 — Direct Competitors (overlap หลาย feature)

### 1. NotebookLM (Google) 🔥 existential threat
- **URL:** notebooklm.google.com
- **Status:** ACTIVE, dominant
- **Pricing:** Free (50 sources/notebook); Plus $7.99-19.99/mo (300 sources, Google AI Pro bundle); Ultra **$249.99/mo** (600 sources)
- **Per-file cap:** 500k words / 200MB
- **Target:** นักเรียน, researcher, analyst
- **Features:** PDF/Doc/Slides/YouTube/audio sources, source-cited Q&A, **Audio Overviews** (podcast generation), Mind Maps, Studio
- **Chat:** ✅ | **API:** limited/none public | **MCP:** ❌
- **BYOS:** ❌ — Google-hosted (Drive linkage as source, not as storage backend)
- **USP:** Google distribution + Gemini quality + free tier
- **Weakness vs PDB:** ไม่มี MCP-out, ไม่มี auto-clustering ข้าม notebooks, free จำกัด 50 source, sources lock ใน notebook silo เดียว

### 2. Notion AI 🟢 owns knowledge worker wedge
- **URL:** notion.com
- **Status:** ACTIVE
- **Pricing:** Free; Plus $10-12/user/mo; Business $20-24/user/mo (AI included — add-on retired May 2025); Enterprise custom
- **Target:** ทีมที่อยู่ Notion อยู่แล้ว
- **Features:** Ask Notion (workspace search), **Custom Agents (3.3, Feb 2026)**, AI autofill, doc generation, Drive/Slack source connectors
- **Files:** native docs + 5MB free / ~5GB paid
- **Chat:** ✅ | **API:** ✅ | **MCP:** ✅ (official Notion MCP server มีแล้ว)
- **BYOS:** ❌ — Notion-hosted
- **USP:** อยู่ที่ work เกิดขึ้นแล้ว
- **Weakness:** Lock AI หลัง Business tier, ไม่มี auto-clustering ของ arbitrary file uploads, file = attachment ไม่ใช่ knowledge

### 3. Mem 2.0 ⚡ relaunched Q1 2026
- **URL:** mem.ai
- **Status:** ACTIVE (relaunched after 1.0 sunset)
- **Pricing:** Free (25 notes + 25 chats/mo); Pro **$12/mo** (unlimited); Teams (sales)
- **Target:** Knowledge worker, founder, writer
- **Features:** Voice mode, agentic chat, offline support, deep search, PDF understanding, meeting briefs (beta)
- **Chat:** ✅ | **API:** ✅ (paid keys) | **MCP:** ❌ ไม่ advertised
- **BYOS:** ❌
- **USP:** Brand recovery + agentic actions on notes
- **Weakness:** ไม่มี MCP, ไม่มี BYOS, ไม่มี knowledge graph viz, file format support อ่อนกว่า PDB

### 4. Pieces.app 🚀 MCP-native (PDB closest spiritual cousin)
- **URL:** pieces.app
- **Status:** ACTIVE — 150k+ users
- **Pricing:** Free desktop core; paid tiers cloud/team
- **Target:** **Developers only** (PDB อยู่ทั่วไป — ตลาดต่าง)
- **Features:** **9-month rolling LTM-2 memory**, Chrome/VS Code/IDE plugins, **MCP server** เชื่อม Claude/Cursor/Copilot/Goose
- **Chat:** ✅ | **API:** ✅ | **MCP:** **first-class** — distribution surface หลัก
- **BYOS:** local-by-default; cloud optional
- **USP:** MCP-as-personal-memory ที่ ship จริงแล้ว
- **Weakness vs PDB:** **dev-only**, จับ activity ไม่ใช่ curated documents, ไม่มี clustering/knowledge-graph สำหรับ general files

### 5. Personal.ai (enterprise pivot)
- **Status:** ACTIVE — pivoted ออกจาก consumer
- **Clients:** Microsoft, NVIDIA, Verizon, AT&T
- **Features:** Memory Core (encoding/storing/retrieving), 6 memory types (episodic/semantic/working/etc.)
- **Chat:** ✅ | **API:** ✅ | **MCP:** ❌ ไม่ headlined
- **BYOS:** ❌
- **USP:** Memory primitives เป็น infrastructure
- **Weakness vs PDB:** ไม่ target individuals แล้ว

---

## 📊 Tier 2 — Adjacent Competitors

### 6. Reflect.app
- $10/mo (annual). GPT-4 + Whisper, networked notes, **E2E-encrypted**, calendar
- ❌ MCP, ❌ BYOS, ❌ auto-clustering ของ file uploads
- 🎯 Polished แต่แคบ (notes only ไม่ใช่ files)

### 7. Saner.ai
- "AI assistant for ADHD" — niche positioning
- อ้างว่ารองรับ file upload + AI memory + chat + MCP
- เล็กที่สุดในรายการ

### 8. Saga.so
- Free (5k AI words/mo, 3 members) / **$8/user/mo**
- 60k users, Drive + Linear integrations, team-collab focus
- ❌ MCP, ❌ auto-clustering

### 9. Capacities.io
- Object-oriented PKM, daily notes, 50k users, **EU-hosted, GDPR-strong**, full export (no lock-in)
- User-funded (no VC pressure)
- AI จำกัด, ❌ MCP

### 10. Tana
- Pivoted to **"AI for meetings"** (early access 2026)
- Supertags + agents complete actual work during meetings
- Enterprise compliance (SOC2, GDPR)
- ❌ BYOS, meeting-centric ไม่ใช่ file-centric

### 11. Humata.ai
- Free (60 pages); Expert $9.99; Team $49/user/mo
- Cited PDF Q&A, "ChatGPT for PDFs"
- API ✅, MCP ❌
- 🎯 Pure document-Q&A — ไม่มี knowledge graph/MCP-out

### 12. ChatPDF
- Free (2 docs/day) + Plus
- PDF/DOCX/PPT/MD/TXT, GPT-4o routing, folder grouping, multilingual
- ❌ MCP, ❌ BYOS — dead simple Q&A

### 13. DocsBot.ai
- 75k users, 3k businesses (Sony, Sentry)
- 30+ source connectors, embeddable widget, agentic RAG, public API, SOC 2
- 🎯 **B2B chatbot-builder** ไม่ใช่ personal — ❌ MCP advertised

### 14. AskYourPDF
- 5M users, web/iOS/Android/Chrome
- Zotero + ChatGPT plugin integration, 40+ free side-tools, dev API
- Light on MCP/BYOS

---

## 📊 Tier 3 — Lateral / Tangential

### 15. Obsidian + Smart Connections + obsidian-mcp-plugin 🎯 **closest spiritual cousin to PDB**
- Local vault + bundled local embeddings (bge-micro-v2) + **MCP-over-HTTP** (localhost:3001)
- Free, **fully local, BYOS-by-design** (vault = your folder)
- ❌ Weakness: assembly required, ไม่มี UX สำหรับ non-technical, ไม่มี clustering UI

### 16. Letta (formerly MemGPT)
- ACTIVE — persistent agents with portable memory
- Desktop/CLI/SDK, MCP-aware
- 🎯 Developer-tool ไม่ใช่ consumer PKM
- AGPL-style openness

### 17. Khoj
- Pivoted into multiple products (Open Paper, Pipali beta, Khoj app)
- Local-first AI co-worker
- Lost some focus

### 18. AnythingLLM
- MIT-licensed, desktop+cloud+self-hosted, multi-LLM, PDF/DOCX/CSV/code, agent skills hub
- 🎯 OSS reference for "personal RAG"
- Local-first ไม่ใช่ BYOS-to-Drive

### 19. Readwise Reader
- ACTIVE (still beta) — Articles/RSS/PDF/YT/EPUB, Ghostreader AI copilot
- Exports to Obsidian/Notion/Roam
- 🎯 Read-it-later + light AI ไม่ใช่ auto-organize files

---

## ☠️ Sunset / Dead (2024-2026)

| Service | When | Why |
|---|---|---|
| **Pocket** (Mozilla) | Shut down 2025-07-08, export disabled 2025-11-12 | Mozilla focus shift |
| **Heyday.xyz** | Defunct 2025 | $6.5M seed (2022) ไม่พอ — แพ้ Notion/Evernote/Roam ใน monetization |
| **Reor (reorproject.org)** | Domain expired (now Chicago restaurant), GitHub archived 2026-03-07 | Local-first AI PKM ขาย ยาก |
| **Roam Research with AI** | Still alive, losing share, no notable AI cadence | |
| **Mem 1.0** | Died, reborn as 2.0 ใน 2026 | |

→ **Lesson:** standalone "AI memory" ที่ไม่มี unique distribution = ไม่รอด Google + Notion gravity

---

## ✨ Where PDB has clear gaps (ไม่มีคู่แข่ง)

### Gap 1: **Auto-clusters + summaries + knowledge graph สำหรับ arbitrary uploaded files**
- NotebookLM ไม่ cluster
- Mem ไม่ visualize
- Humata ไม่ organize
- Obsidian ต้อง link เอง
→ **PDB organizer = uncontested ใน consumer SaaS slot**

### Gap 2: **MCP-out for personal data (general user)**
- Pieces ทำ แต่ devs only
- Obsidian-via-plugin ทำ แต่ technical user
→ **PDB targeting non-developers ด้วย one-click MCP for Claude/ChatGPT/Antigravity = real wedge**

### Gap 3: **BYOS to Google Drive**
- ไม่มี mainstream consumer competitor เก็บไฟล์ใน Drive ของ user
- NotebookLM อ่านจาก Drive **แต่เก็บ embeddings/processed state Google-side**
- Capacities มี GDPR + export แต่ไม่ใช่ BYOS
→ **trust/cost moat ที่จับต้องได้**

### Gap 4: **The bundle**
- ไม่มีใครรวม auto-organize + chat + MCP + BYOS ไว้ในที่เดียว
→ **Each individual feature มีคู่แข่ง; nobody has the bundle**

---

## 🎯 Strategic Implications

PDB's defensibility อยู่ที่ **bundle ไม่ใช่ feature เดี่ยว**:

1. **Document Q&A = commoditized** (Humata/ChatPDF/AskYourPDF) — อย่า lead ด้วยพิตช์นี้, **แพ้แน่นอน**
2. **Notes-with-AI = crowded** (Mem/Reflect/Notion) — ก็แพ้
3. **Google สามารถ crush ทุก feature ที่เลียนแบบ** — แข่งตรงๆ ไม่ได้

### Pitch ที่ should win:
> **"ไฟล์ของคุณอยู่ใน Drive ของคุณ
> Claude/ChatGPT เข้าถึงผ่าน MCP
> Auto-organize เป็น knowledge graph"**

ประโยคเดียวนี้ **eliminate ~80% ของคู่แข่ง**

### Pricing Band ที่เหมาะ (จากที่คู่แข่งตั้ง)
- **Floor:** Notion AI Custom Agents (Feb 2026) ~$10/user/mo
- **Ceiling:** NotebookLM Ultra $249.99/mo
- **Sweet spot สำหรับ PDB:** **$10-15/mo** (ภาษาไทย ~฿299-499/เดือน)

### Watch-list (threats to monitor)
- **Pieces.app** expanding beyond developers → ตรงๆ threats MCP wedge
- **Notion AI Custom Agents** (Feb 2026) → ราคา floor ของตลาด
- **NotebookLM** เพิ่ม Drive write-back → BYOS USP หาย
- **Anthropic/OpenAI** launch native MCP memory layer → infrastructure level threat

### Graveyard warning
**Heyday/Reor/Mem-1.0 ทุกตัวตาย** — บอกชัดว่า standalone "AI memory" **ไม่มี unique distribution channel = ไม่รอด**

PDB's distribution channel ที่ unique ที่สุด = **MCP** (เปิด Claude.ai → เห็น PDB) → ต้อง lead marketing ด้วยตรงนี้

---

## 📌 Sources

- [NotebookLM tier guide 2026](https://www.abisheklakandri.com/blog/notebooklm-tiers-pricing-guide-free-plus-pro-ultra-2026)
- [Mem 2.0 launch](https://get.mem.ai/blog/introducing-mem-2-0)
- [Reflect.app](https://reflect.app)
- [Saner.ai](https://saner.ai)
- [Saga.so](https://saga.so)
- [Reor GitHub archived](https://github.com/reorproject/reor)
- [Heyday shutdown post-mortem](https://dang.ai/tool/ai-memory-assistant-heyday)
- [Humata.ai](https://www.humata.ai)
- [ChatPDF](https://www.chatpdf.com)
- [AskYourPDF](https://askyourpdf.com)
- [DocsBot](https://docsbot.ai)
- [Capacities](https://capacities.io)
- [Tana](https://tana.inc)
- [Letta](https://letta.com)
- [Pieces.app](https://pieces.app)
- [Personal.ai](https://personal.ai)
- [Khoj](https://khoj.dev)
- [AnythingLLM](https://anythingllm.com)
- [Pocket shutdown TechCrunch](https://techcrunch.com/2025/05/27/read-it-later-app-pocket-is-shutting-down-here-are-the-best-alternatives/)
- [Notion 2026 pricing](https://www.notion.com/pricing)
- [Smart Connections + Obsidian MCP](https://3sztof.github.io/posts/obsidian-smart-connections-mcp/)
- [Readwise Reader](https://readwise.io/read)

---

## 🇹🇭 Thai Market Competitor Map

### TL;DR Thai Market — 5 ประโยค

1. **LINE = moat ของตลาดไทย** — 54-56M Thai LINE users → ใครไม่อยู่ LINE = สู้กับ gravity
2. **Thailand leads ASEAN GenAI adoption** — 90%+ นักเรียน, 65% professional ใช้ GenAI แล้ว, market $4.3B by 2030 (CAGR 28%, GenAI 46%)
3. **ไม่มี Thai "second brain" service เลย** — ทุก Thai player เป็นแค่ (a) B2B chatbot/CRM (b) AI infra/LLM lab (c) generic LINE Q&A bot → **PKM = wide-open lane**
4. **Pricing anchor ต่ำ** — Alisa free 50K tokens, Botnoi free 200K points, AIYA จาก ฿990. Thai consumers expect generous free tier; ChatGPT Plus (~฿700) = upper anchor
5. **Thai LLM infra = ฟรี + government-backed** (Pathumma NECTEC, Typhoon SCB10X) → PDB ride ได้สำหรับ cost arbitrage

### Tier 1 Thai — Direct Competitors

#### 1. Alisa AI (alisamaid.com / @Alisa LINE OA) — 3/5 overlap
- **Status:** ACTIVE 2026, GLORY PCL backed (listed company)
- **Pricing:** Free 50K tokens/month; Premium via sub.alisamaid.com
- **Target:** Thai mass-market consumers
- **LINE-native + web companion**
- **USP:** First-mover Thai brand in LINE GenAI
- **Weakness vs PDB:** ❌ ไม่มี file upload/knowledge base, ❌ auto-organize, ❌ MCP, ❌ graph — chat front-end เฉยๆ ไม่ใช่ workspace

#### 2. Botnoi (botnoi.ai) — 2/5 overlap
- **Status:** ACTIVE — Thailand's #1 chatbot platform (well-funded, Botnoi Group)
- **Pricing:** Free 200K points/mo (~40K msgs); subscription tiers
- **Target:** SMB/enterprise (ไม่ใช่ personal)
- **USP:** Best Thai voice/TTS; mature ecosystem
- **Weakness vs PDB:** B2B-only, ไม่มี personal "your data" angle, ไม่ใช่ document-first

#### 3. ZWIZ.AI — 2/5 overlap
- **Status:** ACTIVE — dtac accelerate / 100SID, profitable, unfunded
- **Pricing:** ~฿28,500-35,000/year
- **Target:** Thai e-commerce SMBs (FB/LINE merchants)
- **Weakness vs PDB:** Pure B2B sales tool, ไม่มี personal/student workflow

#### 4. AIYA (aiya.ai) — 2/5 overlap
- **Status:** ACTIVE — founded 2017
- **Pricing:** จาก ฿990/month
- **Target:** Thai retailers, SMB CRM
- **Weakness:** Same as Zwiz — merchant-focused

#### 5. RevisionSuccess — 3/5 overlap (closest student-facing)
- **Status:** ACTIVE — founded by Thai high-schooler, ~1,000 concurrent users
- **Target:** Thai students (school exam prep)
- **Weakness:** Narrow study-tool, ไม่มี persistent knowledge graph, MCP, general document workspace

### Tier 2 Thai — Adjacent

| Service | บทบาท | สถานะ |
|---|---|---|
| **iApp Technology** | Sovereign-AI APIs (Thai OCR, eKYC, Kaitom Voice TTS, NLP) | B2B infra — PDB consumer ของ ไม่ใช่คู่แข่ง |
| **Looloo Technology** | AI consultancy + PresScribe (medical AI 35 hospitals) | Service firm ไม่ใช่ product |
| **VISAI.ai** | VISTEC+depa spinoff, AI Cloud Platform + custom | Enterprise |
| **Pantip MALL** | New 2026 launch — "Agentic Commerce" + trust | Adjacent commerce ไม่ใช่ knowledge — แต่ Pantip brand reach ใหญ่ |
| **Zaapi, Page365, Wisible** | Thai conversational commerce/CRM | Not knowledge tools |
| **NocNoc** | ❌ shutting down May 2026 | dead |
| **ChatBuddy.ai** | ไม่มี Thai-specific product confirmed | non-competitor |

### 🔧 Thai LLM Infrastructure (Cost Lever, ไม่ใช่ Competitor)

| | Status | Why matters to PDB |
|---|---|---|
| **Typhoon (SCB10X / opentyphoon.ai)** | Best-in-class Thai open LLM, Apache 2.0, multimodal Typhoon 2 | **PDB ใช้แทน Anthropic** สำหรับ Thai-heavy workload — ลด cost |
| **Pathumma LLM (NECTEC/NSTDA)** | Government open-source, Thai Parliament adoption | Free, Thai-cultural-context tuned |
| **AI4Thai (NECTEC)** | API platform: Thai NLP, OCR, speech | Free tier — ใช้ Thai OCR ได้ |
| **WangChanGLM (VISTEC + SCB10X)** | Earlier Thai LLM, superseded by Typhoon | reference |

→ **PDB integrate Typhoon/Pathumma เป็น Thai-LLM fallback** = cost moat + "Thai-cultural-context" feature

### LINE Bot Ecosystem ในไทย

**🟢 What's saturated (อย่าทำ):**
- Customer-service bots
- E-commerce CRM bots (Botnoi/Zwiz/AIYA dominate)
- Booking/reservation bots
- Brand bots (Knorr Auntie etc.)
- Broadcast marketing bots

**🟡 What works (มีตัวอย่าง):**
- "Personal assistant in LINE" (Alisa proves demand)
- Translator bots (Ligo)
- Expense trackers
- School/study Q&A bots

**🟢 What's open (PDB sweet spot):**
- ⭐ **Personal knowledge bots ที่จำเอกสารข้าม session** — nobody owns this
- Shareable "Ask my notes" bots ผ่าน LINE OA
- **MCP-bridge bots** ("ask Claude/ChatGPT about my LINE-uploaded files")
- Long-term memory bots สำหรับ student/professional — Alisa stateless

**🔴 What doesn't work:**
- Standalone mobile app without LINE — Thai users ไม่ลงแอปใหม่
- Pure web-app-only — retention แย่

### Thai User Behavior Notes (สำคัญสำหรับ pricing + UX)

1. **Free-first culture, but pay for clear value**
   - Mass tier: ฿99-299/month
   - Pro tier: ฿590-990/month
   - ChatGPT Plus ~฿700 = upper anchor

2. **Payment rails priority:**
   - PromptPay/QR (ที่ 1)
   - TrueMoney
   - Rabbit LINE Pay
   - Stripe (credit card) — แต่ penetration ต่ำกว่า US
   - Annual discount works; auto-renew distrust real

3. **Language:**
   - Thaiglish (mixed Thai+English) = normal
   - Pure-English UI = lose non-Bangkok users
   - Pure-Thai UI = childish to professionals
   - **PDB bilingual approach = correct ✅**

4. **Trust signals:**
   - "สัญชาติไทย" (Thai-made)
   - University/government association
   - Real founder face
   - Active Thai Facebook Page
   - Anonymous SaaS = scammy feel

5. **Adoption pattern:**
   - 🥇 Students lead (90%+ GenAI)
   - 🥈 Professionals follow (65%)
   - 🐌 SMBs slowest
   - Word-of-mouth via LINE groups + TikTok/Facebook reels >> Google search

6. **Privacy concern:** rising but secondary to convenience
   - "Your data stays yours" resonates with professionals/lawyers/doctors
   - Mass students don't care as much

### ✨ Where PDB has clear gaps (Thai market)

1. **Personal knowledge workspace + file upload + auto-organize** — **ZERO Thai players**
2. **MCP integration** — **completely uncontested in Thailand** — massive differentiator with developer/power-user
3. **BYOS / Google Drive** — Thai SaaS uniformly host data themselves; user-controlled storage = unique trust
4. **Knowledge graph viz** — novel ใน Thai market

### 🎯 Strategic Implications for Thai Market

1. **🚀 Ship LINE bot FAST** — Web-app-only PDB จะแพ้ Alisa เรื่อง distribution. **LINE bot ไม่ต้องมี feature parity** — แค่ "upload to LINE → appears in PDB workspace + summary back in chat" loop เดียวก็ unmatched

2. **📛 Position = "Second brain in Thai" (สมองที่สอง)** ไม่ใช่ "another AI chatbot"
   - Chatbot category = bloodbath
   - PKM category = empty

3. **🎯 Target student/professional/freelancer** — ไม่ใช่ SMB
   - Botnoi/Zwiz/AIYA ครอง SMB → suicide ถ้า outflank ตรงนั้น
   - PDB MCP+graph+upload = wasted on shop owners

4. **💰 Cost arbitrage with Typhoon/Pathumma**
   - ใช้สำหรับ Thai summarization/OCR
   - Claude สำหรับ reasoning
   - Market เป็น "Thai-cultural-context feature"

5. **💵 Pricing test:**
   - Free: 5 docs, 100 chats/month
   - Pro: ฿199/month
   - Power: ฿590/month
   - Annual -20% discount
   - PromptPay + Stripe required

6. **🎨 Avoid AI-slop fingerprints**
   - ❌ Gradient hero + robot mascot + "AI ผู้ช่วยอัจฉริยะ" tagline
   - ✅ Refined minimal Thai typography = differentiation in itself

### Thai Sources
- [Alisa AI](https://alisamaid.com/), [@Alisa LINE OA](https://page.line.me/843ejuri)
- [Botnoi.ai](https://botnoi.ai/), [Botnoi Pricing](https://botnoigroup.com/botnoivoice/doc/pricing-packages)
- [ZWIZ.AI Pricing](https://zwiz.ai/en/pricing), [AIYA web](https://web.aiya.ai/)
- [Typhoon SCB10X](https://opentyphoon.ai/), [Typhoon 2](https://www.scb10x.com/en/blog/introducing-typhoon-2-thai-llm)
- [Pathumma LLM NECTEC](https://www.nectec.or.th/innovation/innovation-service/pathumma-llm.html)
- [iApp Technology](https://iapp.co.th/), [Looloo](https://loolootech.com/), [VISAI](https://visai.ai/about)
- [AI for Thai (NECTEC)](https://www.nectec.or.th/innovation/innovation-software/aiforthai.html)
- [Statista Thailand AI](https://www.statista.com/outlook/tmo/artificial-intelligence/thailand)
- [Thailand Leads ASEAN AI](https://www.nationthailand.com/business/tech/40062452)
- [SCBX Thai Consumer AI 2026](https://www.scbx.com/en/news/thai-consumer-ai-adoption-report/)
- [Beacon VC - Thailand AI Boom](https://www.beaconvc.fund/research/decoding-thailands-ai-boom)
- [LINE Statistics 2026](https://expandedramblings.com/index.php/line-statistics/)
- [Stripe Thailand recurring](https://stripe.com/resources/more/membership-systems-with-recurring-payments-thailand)
