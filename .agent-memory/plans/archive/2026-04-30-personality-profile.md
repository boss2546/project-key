# Plan: Personality Profile (MBTI / Enneagram / CliftonStrengths / VIA Strengths) + History

**Author:** แดง (Daeng)
**Date:** 2026-04-30 (final — combines v1's 4 systems + v2's history feature)
**Status:** approved (user confirmed 2026-04-30)

---

## 🎯 Goal

ขยายระบบโปรไฟล์ของ Project KEY ให้รองรับ **personality types 4 ระบบ** ที่นิยมที่สุด + **เก็บประวัติทุกครั้งที่ผู้ใช้อัปเดต** เพื่อให้ AI ปรับการตอบคำถามให้เข้ากับลักษณะนิสัย วิธีคิด และจุดแข็งของผู้ใช้แต่ละคนได้แม่นยำที่สุด — และส่งข้อมูลนี้ผ่าน MCP ไปยัง AI ภายนอก (Claude, Antigravity, ChatGPT) พร้อมกับโปรไฟล์เดิมตอนดึงครั้งเดียว

**4 ระบบที่จะรองรับ:**
1. **MBTI** (Myers-Briggs Type Indicator) — 16 types
2. **Enneagram** — 9 types + wing
3. **CliftonStrengths** — Top 5 themes (จาก 34 themes)
4. **VIA Character Strengths** — Top 5 strengths (จาก 24 strengths)

**ผู้ใช้:**
- ผู้ใช้ที่ทำแบบทดสอบมาแล้ว → กรอกผลเข้าระบบ
- ผู้ใช้ใหม่ที่ยังไม่เคยทำ → ระบบมีลิงก์ไปทำที่เว็บออฟฟิเชียล (ฟรี + เสียเงินตามแต่ละระบบ)
- ผู้ใช้ที่ทำซ้ำในอนาคต → อัปเดตได้, ระบบเก็บประวัติให้

**ทำเสร็จแล้วได้อะไร:**
1. โปรไฟล์เก็บได้ 4 ระบบบุคลิกภาพ — ทั้ง current state + history
2. **เก็บประวัติการอัปเดตทุกครั้ง** (timeline ผ่านเว็บ) — รู้ว่าผลเปลี่ยนยังไงเมื่อไหร่ มาจาก source ใด
3. AI ใน `/api/chat` ตอบโดยรู้จักบุคลิกผู้ใช้ → Layer 1 priority สูงสุด
4. **MCP tool `get_profile` ส่งข้อมูลบุคลิกภาพ + summary ไปพร้อมกับโปรไฟล์เดิม + active_contexts ตอนถูกเรียกครั้งเดียว** — Claude/Antigravity/ChatGPT ใช้ได้ทันที
5. MCP tool `update_profile` รองรับการอัปเดตจาก AI ภายนอก (history บันทึก source = "mcp_update")
6. UI กรอกง่าย (dropdown + searchable list) — ไม่ต้องพิมพ์เอง — collapsible เพื่อไม่บีบ modal
7. ผู้ใช้ที่ไม่รู้ผลของตัวเอง → คลิกลิงก์ไปทำที่เว็บออฟฟิเชียลได้ทันที (3 ใน 4 ระบบมีฟรี)

---

## ✅ Resolved Decisions (จาก user 2026-04-29 + 2026-04-30)

| # | Decision | สถานะใน plan |
|---|---|---|
| Q1 | **4 ระบบ (รวม VIA)** — VIA ฟรีเป็น default คู่กับ Clifton ที่เสียเงิน | ✅ บาก-in |
| Q2 | MVP detail level | ✅ MBTI 4 ตัว / Enneagram core+wing / Clifton+VIA Top 5 |
| Q3 | **เก็บประวัติทุกครั้ง** — ผู้ใช้อัปเดตได้, ระบบ snapshot ไว้ | ✅ table `personality_history` + endpoint + UI |
| Q4 | ส่งทุกช่อง (chat + MCP) ไม่ทำ privacy granular | ✅ ตามแผน |
| Q5 | LLM injection: TH+EN ผสม | ✅ ตามแผน |
| Q6 | คงไว้ทั้ง personality + preferred_output_style เดิม | ✅ ของเดิมไม่แตะ |

---

## 📚 Context

### ระบบโปรไฟล์ปัจจุบัน (v5.9.3)
- 1 ตาราง `user_profiles` — 5 field text เปล่า (`identity_summary`, `goals`, `working_style`, `preferred_output_style`, `background_context`)
- ผู้ใช้พิมพ์เองทั้งหมด → ไม่มี structure → AI ตีความได้ไม่แน่นอน
- โปรไฟล์ถูก inject เข้า LLM prompt 2 ที่:
  1. **Chat retrieval** ([retriever.py:39-114](../../backend/retriever.py#L39-L114)) — Layer 1 priority สูงสุด
  2. **MCP tool `get_profile`** ([mcp_tools.py:477-499](../../backend/mcp_tools.py#L477-L499)) — bundle กับ active_contexts ส่งให้ AI ภายนอก

### ทำไมเลือก 4 ระบบนี้
| ระบบ | จุดเด่น | ทำไมเก็บ | ฟรี? |
|---|---|---|---|
| **MBTI** | นิยมสูงสุด, 16 types | บอกวิธีคิด + รูปแบบการตัดสินใจ | ✅ 16personalities (NERIS) / 💰 mbtionline |
| **Enneagram** | ลึกมิติแรงจูงใจ, 9 types + wing | บอก "ทำไม" ของพฤติกรรม + แรงขับ | ✅ Truity / ✅ Eclectic / 💰 RHETI |
| **CliftonStrengths** | จุดแข็งเชิงงาน, 34 themes | "ใช้คนนี้ทำอะไรได้ดี" | ❌ ฟรีไม่มี / 💰 Gallup เท่านั้น |
| **VIA Character Strengths** | จุดแข็งเชิงคุณค่า, 24 strengths | "คุณค่าที่ขับดันชีวิต" | ✅ ฟรี official ที่ viacharacter.org |

→ **VIA + Clifton เสริมกัน** (เชิงคุณค่า + เชิงงาน). VIA ฟรีเป็น fallback สำหรับผู้ใช้ที่ไม่อยากจ่าย Clifton

### Trademark / Licensing constraint (สำคัญมาก)
- **MBTI®** — ใช้ได้แค่เก็บ user-reported value + ลิงก์ไปเว็บออฟฟิเชียล. ห้ามอ้างว่าเรา administer test
- **CliftonStrengths®** — Gallup ถือลิขสิทธิ์ definitions → **ห้าม copy descriptions ลง UI**. ลิงก์ไป gallup.com/cliftonstrengths เท่านั้น
- **Enneagram** = public domain ✅
- **VIA** = official ฟรี + เปิดให้ใช้ผลส่วนตัว ✅
- → **Strategy:** เก็บค่าผู้ใช้กรอกเอง + link out ไปเว็บออฟฟิเชียล + paraphrase descriptions ที่ส่งให้ LLM (ไม่ copy verbatim ของ Gallup/MBTI Co.)

### "16personalities ≠ MBTI official"
16personalities.com ใช้ NERIS Type Explorer (Big Five hybrid) ไม่ใช่ MBTI จริง — แต่ผู้ใช้ส่วนมากเรียก "MBTI" → เก็บ field `mbti_source` (`official` | `neris` | `self_report`)

---

## 📁 Files to Create / Modify

### Backend (สร้างใหม่ 1 + แก้ 5)
- [ ] `backend/personality.py` (**create**) — reference data (16 MBTI / 9 Enneagram / 34 Clifton / 24 VIA) + helper functions (validate, format_for_llm, get_test_links)
- [ ] `backend/database.py` (modify) — เพิ่ม columns ใน UserProfile + table `personality_history` + idempotent migrations
- [ ] `backend/profile.py` (modify) — extend `get_profile()`, extend `get_profile_context_text()`, **เพิ่ม `record_personality_history()`** + `list_personality_history()`
- [ ] `backend/main.py` (modify) — extend `ProfileRequest`, **เพิ่ม endpoints** GET `/api/profile/personality/history`, GET `/api/personality/reference`
- [ ] `backend/mcp_tools.py` (modify) — extend `update_profile` params + `_tool_get_profile` returns personality data + summary
- [ ] `backend/retriever.py` — **no code change required** (auto-inherits via `get_profile_context_text`)

### Frontend (แก้ 3)
- [ ] `legacy-frontend/index.html` (modify) — เพิ่ม personality section ใน profile-modal + history modal
- [ ] `legacy-frontend/app.js` (modify) — extend loadProfile/saveProfile + dropdown population + history view + i18n keys
- [ ] `legacy-frontend/styles.css` (modify) — style personality blocks + history timeline

### Tests (สำหรับฟ้า — create)
- [ ] `tests/test_personality.py` — unit tests สำหรับ personality.py + integration tests
- [ ] `tests/e2e/test_personality_e2e.py` — E2E flow

### Memory updates (เขียวต้องอัปเดตหลัง implement)
- [ ] `.agent-memory/contracts/api-spec.md` (สร้างถ้ายังไม่มี)
- [ ] `.agent-memory/contracts/data-models.md`

---

## 💾 Data Model Changes

### A) Schema additions to `user_profiles` (current snapshot)

```python
class UserProfile(Base):
    # ─── existing fields (unchanged) ───
    id, user_id, identity_summary, goals, working_style,
    preferred_output_style, background_context, updated_at

    # ─── v6.0 — Personality fields (5 new columns) ───
    mbti_type = Column(String(8), nullable=True)
    # Format: "INTJ" | "INTJ-A" | "INTJ-T" (NERIS suffix optional)
    # NULL = not set

    mbti_source = Column(String(20), nullable=True, default=None)
    # "official" | "neris" | "self_report"

    enneagram_data = Column(Text, nullable=True)
    # JSON: {"core": 1-9, "wing": 1-9 | null}

    clifton_top5 = Column(Text, nullable=True)
    # JSON: ["Strategic", "Learner", "Input", "Analytical", "Achiever"]
    # Order matters (rank 1 → 5)

    via_top5 = Column(Text, nullable=True)
    # JSON: ["Curiosity", "Love of Learning", "Honesty", "Judgment", "Perspective"]
    # Order matters
```

### B) NEW table `personality_history` (append-only log สำหรับ Q3)

```python
class PersonalityHistory(Base):
    """Append-only snapshot log of personality updates."""
    __tablename__ = "personality_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    system = Column(String, nullable=False)
    # Enum: "mbti" | "enneagram" | "clifton" | "via"
    data_json = Column(Text, nullable=False)
    # JSON snapshot of THIS system's value at this point in time
    # MBTI: {"type": "INTJ", "source": "neris"}
    # Enneagram: {"core": 5, "wing": 4}
    # Clifton/VIA: {"top5": ["Strategic", "Learner", ...]}
    # Cleared: {"cleared": true}
    source = Column(String, default="user_update")
    # "user_update" | "mcp_update"
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
```

**Index:** composite index on `(user_id, system, recorded_at desc)`

**Append rule:** เมื่อ `update_profile()` ได้รับ field personality → snapshot ก่อน-หลัง → ถ้า **ค่าเปลี่ยนจริง** → insert row (ไม่ insert ถ้า user ส่งค่าเดิมซ้ำ)

### Migration (in `database.py:init_db()`)

เพิ่มต่อจาก v5.9.3 migration block:

```python
# v6.0 Migration — Personality fields
cursor = await db.execute("PRAGMA table_info(user_profiles)")
profile_cols = [row[1] for row in await cursor.fetchall()]
if "mbti_type" not in profile_cols:
    await db.execute("ALTER TABLE user_profiles ADD COLUMN mbti_type TEXT")
    await db.execute("ALTER TABLE user_profiles ADD COLUMN mbti_source TEXT")
    await db.execute("ALTER TABLE user_profiles ADD COLUMN enneagram_data TEXT")
    await db.execute("ALTER TABLE user_profiles ADD COLUMN clifton_top5 TEXT")
    await db.execute("ALTER TABLE user_profiles ADD COLUMN via_top5 TEXT")
    migrated = True
    print("  → Added: user_profiles.mbti_type, mbti_source, enneagram_data, clifton_top5, via_top5")

# v6.0 — PersonalityHistory table จะถูกสร้างโดย Base.metadata.create_all แล้ว
# เพิ่ม composite index:
try:
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_personality_history_user_system "
        "ON personality_history(user_id, system, recorded_at DESC)"
    )
except Exception as e:
    print(f"  ⚠️ Index creation warning: {e}")
```

ตามกฎ migration: idempotent ✅, additive only ✅, auto-backup จะรันก่อนอยู่แล้ว ✅

---

## 📡 API Changes

### GET /api/profile (modified — backward compatible)

**Response 200** เพิ่ม 4 fields ใหม่ (อาจ null):
```json
{
  "exists": true,
  "identity_summary": "...",
  ...existing 5 fields...,
  "mbti": {"type": "INTJ", "source": "neris"} | null,
  "enneagram": {"core": 5, "wing": 4} | null,
  "clifton_top5": ["Strategic", "Learner", "Input", "Analytical", "Achiever"] | null,
  "via_top5": ["Curiosity", "Love of Learning", "Honesty", "Judgment", "Perspective"] | null,
  "updated_at": "ISO"
}
```

### PUT /api/profile (modified)

**Request body:**
```json
{
  ...existing 5 fields...,
  "mbti": {"type": "INTJ", "source": "neris"},   // new
  "enneagram": {"core": 5, "wing": 4},             // new
  "clifton_top5": ["Strategic", "..."],             // new (1-5 items)
  "via_top5": ["Curiosity", "..."]                  // new (1-5 items)
}
```

**Behavior:**
- ส่ง `null` → field ถูก clear (DB NULL, history บันทึก clear event)
- ไม่ส่ง field → field ไม่เปลี่ยน
- ส่ง `[]` สำหรับ clifton_top5/via_top5 → ถือเป็น clear

**Errors:**
- 400 `INVALID_MBTI_TYPE` — type ไม่อยู่ใน 16 ค่ามาตรฐาน
- 400 `INVALID_MBTI_SOURCE` — source ไม่อยู่ใน {"official", "neris", "self_report"}
- 400 `INVALID_ENNEAGRAM_CORE` — core ไม่ใช่ 1-9
- 400 `INVALID_ENNEAGRAM_WING` — wing ไม่ใช่ ±1 ของ core (รวม wrap-around)
- 400 `INVALID_CLIFTON_THEME` — theme ไม่อยู่ใน 34 themes มาตรฐาน + รายการ
- 400 `INVALID_VIA_STRENGTH` — strength ไม่อยู่ใน 24 strengths มาตรฐาน + รายการ
- 400 `TOO_MANY_TOP5` — clifton/via array > 5 items
- 400 `DUPLICATE_THEMES` — clifton/via มีค่าซ้ำใน top5
- 401 — ตามปกติ

### NEW: GET /api/profile/personality/history

**Auth:** Required (JWT)

**Query params:**
- `system` (optional) — `"mbti"` | `"enneagram"` | `"clifton"` | `"via"` — filter
- `limit` (optional, default=50, max=200)

**Response 200:**
```json
{
  "history": [
    {
      "id": 12,
      "system": "mbti",
      "data": {"type": "ENFP", "source": "official"},
      "source": "user_update",
      "recorded_at": "2026-04-30T15:30:00"
    },
    {
      "id": 11,
      "system": "mbti",
      "data": {"type": "INTJ", "source": "neris"},
      "source": "user_update",
      "recorded_at": "2026-04-15T10:00:00"
    }
  ],
  "count": 2
}
```

### NEW: GET /api/personality/reference (no auth — public reference data)

**Response 200:**
```json
{
  "mbti": {
    "types": ["ISTJ", "ISFJ", ..., "ENTJ"],
    "sources": ["official", "neris", "self_report"],
    "test_links": [
      {"name": "16personalities (ฟรี)", "url": "...", "cost": "free", "note": "..."},
      {"name": "MBTI Online (Official)", "url": "...", "cost": "$50 USD"}
    ]
  },
  "enneagram": {
    "types": {"1": {"th": "นักปฏิรูป", "en": "The Reformer"}, ...},
    "test_links": [...]
  },
  "clifton": {
    "domains": {"executing": [...], "influencing": [...], "relationship_building": [...], "strategic_thinking": [...]},
    "all": [...34 themes...],
    "test_links": [...]
  },
  "via": {
    "virtues": {"wisdom": [...], "courage": [...], "humanity": [...], "justice": [...], "temperance": [...], "transcendence": [...]},
    "all": [...24 strengths...],
    "test_links": [...]
  }
}
```

### MCP tool — `update_profile` (modified)

เพิ่ม params:
```python
"update_profile": {
    "params": [
        # ─── existing 5 fields ───
        ...
        # ─── new — personality (all optional) ───
        {"name": "mbti_type", "type": "string", "required": False,
         "description": "MBTI 4-letter code (e.g., 'INTJ' or 'INTJ-A')"},
        {"name": "mbti_source", "type": "string", "required": False,
         "description": "Source: 'official', 'neris', or 'self_report'"},
        {"name": "enneagram_core", "type": "integer", "required": False,
         "description": "Enneagram core type 1-9"},
        {"name": "enneagram_wing", "type": "integer", "required": False,
         "description": "Enneagram wing 1-9 (must be ±1 of core, wrap-around)"},
        {"name": "clifton_top5", "type": "array", "required": False,
         "description": "Top 5 CliftonStrengths themes in order (1-5 items)"},
        {"name": "via_top5", "type": "array", "required": False,
         "description": "Top 5 VIA Character Strengths in order (1-5 items)"},
    ],
}
```

→ MCP update ก็ snapshot history (source = `"mcp_update"`)

### MCP tool — `get_profile` (modified output) — ⭐ CRITICAL

**ส่งทุกอย่างไปพร้อมกันตอนถูกเรียกครั้งเดียว** — Claude/Antigravity/ChatGPT ใช้ได้ทันที

```json
{
  "identity_summary": "...",
  "goals": "...",
  "working_style": "...",
  "preferred_output_style": "...",
  "background_context": "...",

  // NEW — personality fields ทั้ง 4 ระบบ
  "mbti": {"type": "INTJ-A", "source": "neris"},
  "enneagram": {"core": 5, "wing": 4},
  "clifton_top5": ["Strategic", "Learner", "Input", "Analytical", "Achiever"],
  "via_top5": ["Curiosity", "Love of Learning", "Honesty", "Judgment", "Perspective"],

  // NEW — บรรทัดเดียวสรุปบุคลิก ให้ AI ใช้ทันทีโดยไม่ต้อง parse
  "personality_summary": "INTJ-A | Enneagram 5w4 | Clifton: Strategic+Learner+Input | VIA: Curiosity+Love of Learning. Strategic thinker; values logic, evidence, depth, autonomy.",

  // EXISTING (v5.5)
  "active_contexts": [
    {"context_id": "...", "title": "...", "summary": "...", ...}
  ],
  "active_contexts_count": 3,
  "tip": "Active contexts are included. Use load_context(context_id) to get full content."
}
```

`personality_summary` — บรรทัดเดียวที่ AI ใช้ได้ทันที (ไม่ต้อง interpret โครงสร้าง 4 ระบบ)

### MCP — ไม่เพิ่ม tool ใหม่สำหรับ history (web-only feature ใน MVP)
ถ้าต้องการ history ผ่าน MCP ในอนาคต ค่อยเพิ่ม `get_personality_history`

---

## 🎨 UX / Frontend Changes

### Profile Modal — เพิ่ม "💎 Personality" section + history link

```
┌─────────────────────────────────────────────────────┐
│ 👤 My Profile                                  [✕]  │
├─────────────────────────────────────────────────────┤
│ [Billing card — existing]                            │
│ [Usage bars — existing]                              │
│ ─────────────────────────────────────────────       │
│                                                      │
│ 💎 Personality (ไม่บังคับ)             [▼ ขยาย]   │
│   ↓ คลิกเพื่อขยาย — ปิดเป็น default                │
│                                                      │
│ ┌─ MBTI ────────────────  [📜 ประวัติ (3) ──────┐  │
│ │ ประเภท: [Dropdown 16 types ▼] [INTJ]          │  │
│ │ Identity: [— / -A / -T ▼] (สำหรับ NERIS)      │  │
│ │ Source: ( ) Official  (•) 16personalities      │  │
│ │         ( ) ฉันเดาเอง                          │  │
│ │ ❓ ไม่รู้? → [16personalities (ฟรี) ↗]         │  │
│ │             [MBTI Online ($50) ↗]              │  │
│ └────────────────────────────────────────────────┘  │
│                                                      │
│ ┌─ Enneagram ──────────  [📜 ประวัติ (1) ───────┐  │
│ │ Core: [1-9 dropdown ▼] [5 — นักสำรวจ]          │  │
│ │ Wing: [4 ▼ or 6 ▼] (auto-disabled if no core)  │  │
│ │ ❓ ไม่รู้? → [Truity (ฟรี) ↗]                   │  │
│ │             [Eclectic Energies (ฟรี) ↗]        │  │
│ │             [Enneagram Institute ($12) ↗]      │  │
│ └────────────────────────────────────────────────┘  │
│                                                      │
│ ┌─ CliftonStrengths Top 5  [📜 ประวัติ (2) ────┐  │
│ │ #1: [searchable dropdown — 34 themes]          │  │
│ │ #2-5: [...]                                     │  │
│ │ ❓ ไม่รู้? → [Gallup ($25-60) ↗]               │  │
│ │   ⚠️ Gallup เป็นเว็บเดียวที่ official —        │  │
│ │      ไม่มีเวอร์ชันฟรี                          │  │
│ └────────────────────────────────────────────────┘  │
│                                                      │
│ ┌─ VIA Character Strengths  [📜 ประวัติ (1) ───┐  │
│ │ #1: [searchable dropdown — 24 strengths]       │  │
│ │ #2-5: [...]                                     │  │
│ │ ❓ ไม่รู้? → [VIA Institute (ฟรี!) ↗]           │  │
│ │   💡 ฟรี official — แนะนำให้ลอง                │  │
│ └────────────────────────────────────────────────┘  │
│                                                      │
│ ─────────────────────────────────────────────       │
│ [existing 5 textarea fields — unchanged]            │
│                                                      │
│            [💾 บันทึกโปรไฟล์]                       │
└─────────────────────────────────────────────────────┘
```

### History Modal (NEW — เปิดเมื่อคลิก "📜 ประวัติ")

```
┌─────────────────────────────────────────────────────┐
│ 📜 ประวัติ MBTI                                [✕]  │
├─────────────────────────────────────────────────────┤
│  📅 2026-04-30 15:30   ENFP-A   (official)         │
│      อัปเดตจาก: เว็บไซต์ project-key                │
│  ─────────────                                      │
│  📅 2026-04-15 10:00   INTJ-T   (neris)            │
│      อัปเดตจาก: เว็บไซต์ project-key                │
│  ─────────────                                      │
│  📅 2026-03-20 09:00   INTJ     (self_report)      │
│      อัปเดตจาก: Claude (MCP)                        │
└─────────────────────────────────────────────────────┘
```

**Format ของแต่ละระบบใน history:**
- **MBTI:** type + source
- **Enneagram:** core + wing (เช่น "5w4")
- **Clifton/VIA:** Top 5 list (comma-separated)

### "ฉันไม่รู้" link spec
- Icon `↗` (external link)
- `target="_blank" rel="noopener noreferrer"` — ห้าม leak `window.opener`
- แสดง **(ฟรี)** หรือ **(฿XX)** ตามต้นทุน
- เปิด tab ใหม่ — ไม่ embed iframe
- มี note PDPA: "การคลิกลิงก์จะส่งคุณไปยังเว็บไซต์ภายนอก — โปรดดูนโยบายความเป็นส่วนตัวของเว็บนั้น"

### Searchable dropdown (Clifton 34 themes / VIA 24 strengths)
- ใช้ `<input list="...">` + `<datalist>` — native, ไม่ต้องโหลด library
- Top 5 = 5 แถว → validate frontend: ห้ามซ้ำ, ห้ามว่างถ้าแถวก่อนหน้ามีค่า

### Wing dropdown logic (Enneagram wrap-around)
- core = 4 → wings = 3, 5
- core = 9 → wings = 8, 1 (wrap-around)
- core = 1 → wings = 9, 2 (wrap-around)
- ก่อนเลือก core → wing dropdown disabled

### Empty state
- Section "💎 Personality" ปิดเป็น default — title มี "(ไม่บังคับ)" ชัดเจน

---

## 📚 Reference Data Specification

ในไฟล์ `backend/personality.py` ต้องมี constants ครบ:

### `MBTI` (16 types + 3 sources + 2 test links)
```python
MBTI_TYPES = [
    "ISTJ", "ISFJ", "INFJ", "INTJ",
    "ISTP", "ISFP", "INFP", "INTP",
    "ESTP", "ESFP", "ENFP", "ENTP",
    "ESTJ", "ESFJ", "ENFJ", "ENTJ",
]
MBTI_SOURCES = ["official", "neris", "self_report"]
MBTI_TEST_LINKS = [
    {"name": "16personalities (ฟรี)",
     "url": "https://www.16personalities.com/",
     "cost": "free",
     "note": "ใช้ NERIS Type Explorer — คล้าย MBTI แต่ไม่ใช่ official"},
    {"name": "MBTI Online (Official)",
     "url": "https://www.mbtionline.com/",
     "cost": "$50 USD",
     "note": "ของบริษัทเจ้าของลิขสิทธิ์ MBTI"},
]
```

### `ENNEAGRAM` (9 types TH+EN + 3 test links)
```python
ENNEAGRAM_TYPES = {
    1: {"th": "นักปฏิรูป", "en": "The Reformer"},
    2: {"th": "ผู้ช่วยเหลือ", "en": "The Helper"},
    3: {"th": "ผู้บรรลุ", "en": "The Achiever"},
    4: {"th": "ผู้มีเอกลักษณ์", "en": "The Individualist"},
    5: {"th": "นักสำรวจ", "en": "The Investigator"},
    6: {"th": "ผู้ภักดี", "en": "The Loyalist"},
    7: {"th": "นักผจญภัย", "en": "The Enthusiast"},
    8: {"th": "นักท้าทาย", "en": "The Challenger"},
    9: {"th": "ผู้สร้างสันติ", "en": "The Peacemaker"},
}
ENNEAGRAM_TEST_LINKS = [
    {"name": "Truity (ฟรี)",
     "url": "https://www.truity.com/test/enneagram-personality-test",
     "cost": "free"},
    {"name": "Eclectic Energies (ฟรี, ไม่ต้องใช้อีเมล)",
     "url": "https://www.eclecticenergies.com/enneagram/test",
     "cost": "free"},
    {"name": "Enneagram Institute RHETI",
     "url": "https://www.enneagraminstitute.com/",
     "cost": "$12 USD"},
]
```

### `CLIFTON` (34 themes / 4 domains + 2 test links)
```python
CLIFTON_THEMES = {
    "executing": ["Achiever", "Arranger", "Belief", "Consistency", "Deliberative",
                  "Discipline", "Focus", "Responsibility", "Restorative"],
    "influencing": ["Activator", "Command", "Communication", "Competition",
                    "Maximizer", "Self-Assurance", "Significance", "Woo"],
    "relationship_building": ["Adaptability", "Connectedness", "Developer", "Empathy",
                              "Harmony", "Includer", "Individualization", "Positivity", "Relator"],
    "strategic_thinking": ["Analytical", "Context", "Futuristic", "Ideation", "Input",
                           "Intellection", "Learner", "Strategic"],
}
CLIFTON_ALL_THEMES = sum(CLIFTON_THEMES.values(), [])  # 34 ค่า
CLIFTON_TEST_LINKS = [
    {"name": "Gallup CliftonStrengths Top 5",
     "url": "https://www.gallup.com/cliftonstrengths/en/home.aspx",
     "cost": "$24.99 USD",
     "note": "Gallup เป็นเว็บเดียวที่ official — ไม่มีเวอร์ชันฟรี"},
    {"name": "Gallup CliftonStrengths Full 34",
     "url": "https://www.gallup.com/cliftonstrengths/en/home.aspx",
     "cost": "$59.99 USD"},
]
```

⚠️ **ห้ามเขียน descriptions ของแต่ละ Clifton theme ใน UI** (Gallup ถือลิขสิทธิ์)

### `VIA` (24 strengths / 6 virtues + 1 free official test link)
```python
VIA_STRENGTHS = {
    "wisdom": ["Creativity", "Curiosity", "Judgment", "Love of Learning", "Perspective"],
    "courage": ["Bravery", "Perseverance", "Honesty", "Zest"],
    "humanity": ["Love", "Kindness", "Social Intelligence"],
    "justice": ["Teamwork", "Fairness", "Leadership"],
    "temperance": ["Forgiveness", "Humility", "Prudence", "Self-Regulation"],
    "transcendence": ["Appreciation of Beauty & Excellence", "Gratitude", "Hope", "Humor", "Spirituality"],
}
VIA_ALL_STRENGTHS = sum(VIA_STRENGTHS.values(), [])  # 24 ค่า
VIA_TEST_LINKS = [
    {"name": "VIA Institute (ฟรี — official)",
     "url": "https://www.viacharacter.org/",
     "cost": "free",
     "note": "official + ฟรี + แนะนำที่สุด"},
]
```

### Validation helpers
```python
def validate_mbti(value: str) -> bool:
    """INTJ, INTJ-A, INTJ-T allowed."""
    if not value: return False
    parts = value.split("-")
    base = parts[0]
    suffix = parts[1] if len(parts) == 2 else None
    return base in MBTI_TYPES and (suffix is None or suffix in ("A", "T"))

def get_enneagram_wings(core: int) -> tuple[int, int]:
    """Return 2 valid wings with wrap-around.
    Examples: core=4 → (3,5); core=9 → (8,1); core=1 → (9,2).
    """
    if not (1 <= core <= 9):
        raise ValueError(f"Invalid core: {core}")
    left = core - 1 if core > 1 else 9
    right = core + 1 if core < 9 else 1
    return (left, right)

def validate_enneagram(core: int, wing: int | None) -> bool:
    if not (1 <= core <= 9): return False
    if wing is None: return True
    return wing in get_enneagram_wings(core)

def validate_clifton(themes: list[str]) -> tuple[bool, list[str]]:
    if len(themes) > 5: return (False, ["TOO_MANY"])
    if len(set(themes)) != len(themes): return (False, ["DUPLICATE"])
    invalid = [t for t in themes if t not in CLIFTON_ALL_THEMES]
    return (len(invalid) == 0, invalid)

def validate_via(strengths: list[str]) -> tuple[bool, list[str]]:
    if len(strengths) > 5: return (False, ["TOO_MANY"])
    if len(set(strengths)) != len(strengths): return (False, ["DUPLICATE"])
    invalid = [s for s in strengths if s not in VIA_ALL_STRENGTHS]
    return (len(invalid) == 0, invalid)
```

### LLM-injection helpers (TH+EN ผสม per Q5)
```python
def format_personality_for_llm(profile: dict) -> str:
    """Build personality block in TH+EN mixed for LLM context.
    Returns "" if no personality data set.
    """
    parts = []
    if profile.get("mbti"):
        mbti = profile["mbti"]
        src = mbti.get("source", "self")
        parts.append(f"MBTI: {mbti['type']} (source: {src})")
    if profile.get("enneagram"):
        e = profile["enneagram"]
        wing_str = f"w{e['wing']}" if e.get("wing") else ""
        type_th = ENNEAGRAM_TYPES.get(e["core"], {}).get("th", "")
        type_en = ENNEAGRAM_TYPES.get(e["core"], {}).get("en", "")
        parts.append(f"Enneagram: {e['core']}{wing_str} ({type_th} / {type_en})")
    if profile.get("clifton_top5"):
        parts.append(f"จุดแข็งงาน CliftonStrengths Top 5: {', '.join(profile['clifton_top5'])}")
    if profile.get("via_top5"):
        parts.append(f"คุณค่าหลัก VIA Top 5: {', '.join(profile['via_top5'])}")
    if not parts:
        return ""
    return "=== PERSONALITY PROFILE ===\n" + "\n".join(parts) + "\n=== END PERSONALITY ==="

def build_personality_summary(profile: dict) -> str:
    """One-liner summary for MCP get_profile (AI uses directly)."""
    bits = []
    if profile.get("mbti"):
        bits.append(profile["mbti"]["type"])
    if profile.get("enneagram"):
        e = profile["enneagram"]
        wing = f"w{e['wing']}" if e.get("wing") else ""
        bits.append(f"Enneagram {e['core']}{wing}")
    if profile.get("clifton_top5"):
        top3 = " + ".join(profile["clifton_top5"][:3])
        bits.append(f"Clifton: {top3}")
    if profile.get("via_top5"):
        top2 = " + ".join(profile["via_top5"][:2])
        bits.append(f"VIA: {top2}")
    return " | ".join(bits) if bits else ""
```

---

## 🔧 Step-by-Step Implementation (สำหรับเขียว)

### Step 1: Reference data + helpers
1. สร้าง `backend/personality.py`:
   - คัด constants ทั้งหมดจาก section "Reference Data" ข้างบน (4 ระบบ ครบ)
   - Implement `validate_mbti`, `validate_enneagram`, `validate_clifton`, `validate_via`, `get_enneagram_wings`
   - Implement `format_personality_for_llm`, `build_personality_summary`
   - เพิ่ม helper `get_test_links(system: str) -> list`

### Step 2: Database — schema + history table + migration
1. แก้ `backend/database.py`:
   - เพิ่ม 5 columns ใน `UserProfile` class
   - เพิ่ม class `PersonalityHistory(Base)` ตาม spec
   - เพิ่ม v6.0 migration block ใน `init_db()` หลัง v5.9.3 block
2. **Test migration:**
   - รัน server local ครั้งแรก → backup ของ DB ออก → migration รัน → ตรวจ schema ตรง
   - ทดสอบ migration บน DB เก่า v5.9.3 ที่มีข้อมูลผู้ใช้แล้ว

### Step 3: Service layer — profile + history
1. แก้ `backend/profile.py`:
   - extend `get_profile()` deserialize 4 fields ใหม่:
     ```python
     mbti = {"type": profile.mbti_type, "source": profile.mbti_source} if profile.mbti_type else None
     enneagram = json.loads(profile.enneagram_data) if profile.enneagram_data else None
     clifton_top5 = json.loads(profile.clifton_top5) if profile.clifton_top5 else None
     via_top5 = json.loads(profile.via_top5) if profile.via_top5 else None
     ```
   - extend `update_profile()` รับ structure ใหม่ + **บันทึกประวัติ:**
     ```python
     # ก่อน update — get current value เพื่อ compare
     prev_mbti = {...} if profile.mbti_type else None
     prev_enneagram = json.loads(profile.enneagram_data) if profile.enneagram_data else None
     prev_clifton = json.loads(profile.clifton_top5) if profile.clifton_top5 else None
     prev_via = json.loads(profile.via_top5) if profile.via_top5 else None

     # update fields ตามปกติ ...

     # บันทึก history เฉพาะระบบที่ค่าเปลี่ยนจริง
     source_str = data.pop("_history_source", "user_update")
     if "mbti" in data:
         new_val = {...} if profile.mbti_type else None
         if new_val != prev_mbti:
             await record_personality_history(db, user_id, "mbti",
                                              new_val or {"cleared": True}, source_str)
     # เหมือนกันสำหรับ enneagram, clifton, via
     ```
   - เพิ่ม `record_personality_history(db, user_id, system, data, source)` — insert PersonalityHistory row
   - เพิ่ม `list_personality_history(db, user_id, system=None, limit=50)` — query เรียง recorded_at desc
   - extend `get_profile_context_text()` — เรียก `format_personality_for_llm()` ต่อท้าย:
     ```python
     base_text = "=== USER PROFILE ===\n" + ...   # existing
     personality_text = format_personality_for_llm(profile_data)
     return base_text + ("\n\n" + personality_text if personality_text else "")
     ```
   - extend `is_profile_complete()` — เพิ่มเงื่อนไข OR กับ personality fields

### Step 4: API layer
1. แก้ `backend/main.py`:
   - extend `ProfileRequest` Pydantic model ด้วย sub-models `MBTIData`, `EnneagramData` (ใช้ Pydantic validators)
   - **เปลี่ยน convention** จาก `exclude_none=True` → `exclude_unset=True`:
     ```python
     data = req.model_dump(exclude_unset=True)
     data["_history_source"] = "user_update"
     ```
     ⚠️ **กระทบ field เก่าด้วย** → regression test profile fields เก่า 5 ตัว
   - validator สำหรับ clifton/via ใน api_update_profile (ไม่ inline ใน Pydantic เพราะอยาก error message ละเอียด):
     ```python
     if req.clifton_top5 is not None and req.clifton_top5:
         from .personality import validate_clifton
         ok, invalid = validate_clifton(req.clifton_top5)
         if not ok: raise HTTPException(400, f"INVALID_CLIFTON_THEME: {invalid}")
     # เหมือนกันสำหรับ via_top5
     ```
   - เพิ่ม endpoint `/api/personality/reference` (no auth)
   - เพิ่ม endpoint `/api/profile/personality/history` (JWT required):
     ```python
     @app.get("/api/profile/personality/history")
     async def api_get_personality_history(
         system: str | None = None,
         limit: int = Query(50, ge=1, le=200),
         current_user: User = Depends(get_current_user),
         db: AsyncSession = Depends(get_db),
     ):
         from .profile import list_personality_history
         if system and system not in ("mbti", "enneagram", "clifton", "via"):
             raise HTTPException(400, "INVALID_SYSTEM")
         history = await list_personality_history(db, current_user.id, system, limit)
         return {"history": history, "count": len(history)}
     ```

### Step 5: MCP tool layer
1. แก้ `backend/mcp_tools.py`:
   - extend `TOOL_REGISTRY["update_profile"].params` เพิ่ม 6 params (mbti_type, mbti_source, enneagram_core, enneagram_wing, clifton_top5, via_top5)
   - แก้ `_tool_update_profile()` — translate flat params เป็น structured + validate + **mark `_history_source = "mcp_update"`**:
     ```python
     async def _tool_update_profile(db, user_id, params):
         updates = {}
         # existing 5 fields ...

         if params.get("mbti_type"):
             from .personality import validate_mbti, MBTI_SOURCES
             if not validate_mbti(params["mbti_type"]):
                 return {"error": f"INVALID_MBTI_TYPE: {params['mbti_type']}"}
             src = params.get("mbti_source", "self_report")
             if src not in MBTI_SOURCES:
                 return {"error": f"INVALID_MBTI_SOURCE: {src}"}
             updates["mbti"] = {"type": params["mbti_type"], "source": src}

         if params.get("enneagram_core"):
             core = params["enneagram_core"]
             wing = params.get("enneagram_wing")
             from .personality import validate_enneagram
             if not validate_enneagram(core, wing):
                 return {"error": f"INVALID_ENNEAGRAM: core={core}, wing={wing}"}
             updates["enneagram"] = {"core": core, "wing": wing}

         if params.get("clifton_top5"):
             from .personality import validate_clifton
             ok, invalid = validate_clifton(params["clifton_top5"])
             if not ok: return {"error": f"INVALID_CLIFTON: {invalid}"}
             updates["clifton_top5"] = params["clifton_top5"]

         if params.get("via_top5"):
             from .personality import validate_via
             ok, invalid = validate_via(params["via_top5"])
             if not ok: return {"error": f"INVALID_VIA: {invalid}"}
             updates["via_top5"] = params["via_top5"]

         if not updates:
             return {"error": "No profile fields provided to update"}

         updates["_history_source"] = "mcp_update"
         await update_profile(db, user_id, updates)
         return {"status": "updated", "updated_fields": [k for k in updates if not k.startswith("_")]}
     ```
   - แก้ `_tool_get_profile()` — เพิ่ม personality fields + summary **(ส่งทั้งหมดไปพร้อมกันตอนถูกเรียก ครั้งเดียว)**:
     ```python
     # หลัง bundle active_contexts
     from .personality import build_personality_summary
     if profile.get("mbti"):
         result["mbti"] = profile["mbti"]
     if profile.get("enneagram"):
         result["enneagram"] = profile["enneagram"]
     if profile.get("clifton_top5"):
         result["clifton_top5"] = profile["clifton_top5"]
     if profile.get("via_top5"):
         result["via_top5"] = profile["via_top5"]
     summary = build_personality_summary(profile)
     if summary:
         result["personality_summary"] = summary
     ```

### Step 6: Frontend — modal + history view
1. แก้ `legacy-frontend/index.html`:
   - เพิ่ม personality `<details>` section ใน `#profile-modal .modal-body` (4 blocks: MBTI / Enneagram / Clifton / VIA)
   - เพิ่ม HTML สำหรับ history modal `#personality-history-modal`
2. แก้ `legacy-frontend/app.js`:
   - เพิ่ม `loadPersonalityReference()` — fetch `/api/personality/reference` (cache ใน sessionStorage `personality_ref_v1`)
   - เพิ่ม `populatePersonalityDropdowns(refData)` — fill option ทุก dropdown (4 ระบบ)
   - เพิ่ม `renderTestLinks(blockId, links)` — สร้าง `<a>` tags + rel/target
   - เพิ่ม `updateEnneagramWingOptions(coreVal)` — disable wings ที่ไม่ valid
   - แก้ `loadProfile()` — เพิ่ม fill 4 ระบบ + อัปเดต history count badges
   - แก้ `saveProfile()`:
     ```javascript
     const data = {
       // existing 5 fields ...
       mbti: getMbtiInput(),
       enneagram: getEnneagramInput(),
       clifton_top5: getCliftonInput(),
       via_top5: getViaInput(),
     };
     ```
   - เพิ่ม `loadPersonalityHistory(system)` + `renderHistoryModal(history)` — fetch `/api/profile/personality/history?system=X`
   - เพิ่ม event listeners บน "📜 ประวัติ" buttons → เปิด history modal
   - เพิ่ม i18n keys (TH+EN) — labels, "ไม่รู้?", history modal, PDPA notice
3. แก้ `legacy-frontend/styles.css`:
   - Style `.personality-section` (collapsible)
   - Style `.personality-block` (cards within section — 4 blocks)
   - Style `.test-link-chip` (button-style external links)
   - Style `.history-timeline` + `.history-entry`

### Step 7: Verify (เขียวต้องทำเองก่อนส่งฟ้า)
1. รัน server local
2. Register user ใหม่ → เปิด profile modal → ขยาย personality section
3. กรอกครบทั้ง 4 ระบบ:
   - MBTI = INTJ-A (NERIS)
   - Enneagram = 5w4
   - Clifton Top 5 = [Strategic, Learner, Input, Analytical, Achiever]
   - VIA Top 5 = [Curiosity, Love of Learning, Honesty, Judgment, Perspective]
4. Save → Refresh page → เปิด modal อีกครั้ง → เห็นค่าครบ
5. แก้ MBTI เป็น ENFP → save → คลิก "📜 ประวัติ MBTI" → เห็น 2 entries
6. ตรวจ DB:
   - `SELECT mbti_type, enneagram_data, clifton_top5, via_top5 FROM user_profiles WHERE user_id=...`
   - `SELECT * FROM personality_history WHERE user_id=... ORDER BY recorded_at DESC`
7. POST /api/chat → ถามคำถาม → response.profile_used = true → injection_summary มี "โปรไฟล์ผู้ใช้"
8. **เรียก MCP `get_profile`** → ⭐ ตรวจว่าคืนทุกอย่างพร้อมกันในการเรียกครั้งเดียว:
   - 5 profile fields เดิม
   - mbti, enneagram, clifton_top5, via_top5
   - personality_summary (1 บรรทัด)
   - active_contexts (เดิม v5.5)
9. เรียก MCP `update_profile` → ตรวจ history บันทึก source = "mcp_update"
10. ทดสอบ invalid input ครบทุก system
11. คลิกลิงก์ "ทำที่ ..." → tab ใหม่ → URL ถูก

---

## 🧪 Test Scenarios (สำหรับฟ้า)

### Happy Path
1. **ตั้งค่า MBTI ครั้งแรก** + history snapshot
2. **อัปเดต MBTI ครั้งที่ 2** — history เก็บ 2 entries
3. **อัปเดตค่าเดิมซ้ำ** — ไม่ append history (dedup)
4. **ตั้งค่า 4 ระบบพร้อมกัน** — history บันทึก 4 row
5. **Chat ใช้ personality** — profile_used = true + ContextInjectionLog ถูก
6. **MCP get_profile ส่งทุกอย่างพร้อมกัน** — 4 ระบบ + summary + active_contexts ในการเรียกครั้งเดียว
7. **MCP update_profile** → history source = mcp_update
8. **List history แบบไม่ filter system** — return ทุก system รวมกัน เรียง desc

### Validation Errors
- MBTI type = `"XXXX"` → 400 INVALID_MBTI_TYPE
- MBTI type = `"INTJ-X"` (suffix ผิด) → 400
- MBTI source = `"random"` → 400 INVALID_MBTI_SOURCE
- Enneagram core = 10 → 400 INVALID_ENNEAGRAM_CORE
- Enneagram core = 0 → 400
- Enneagram core = 4, wing = 7 → 400 INVALID_ENNEAGRAM_WING
- Enneagram core = 9, wing = 1 → **200** (wrap-around — wings ของ 9 = 8, 1)
- Enneagram core = 1, wing = 9 → **200** (wrap-around)
- Clifton top5 = `["NotARealTheme"]` → 400 INVALID_CLIFTON_THEME + ระบุ ["NotARealTheme"]
- Clifton/VIA top5 ยาว 6 → 400 TOO_MANY_TOP5
- Clifton/VIA top5 ค่าซ้ำ → 400 DUPLICATE_THEMES
- VIA top5 = `["FakeStrength"]` → 400 INVALID_VIA_STRENGTH
- GET /api/profile/personality/history?system=invalid → 400 INVALID_SYSTEM
- GET history?limit=300 → 422 (max=200)

### Auth Errors
- ทุก endpoint JWT — ส่งโดยไม่มี token → 401
- Token หมดอายุ → 401
- `/api/personality/reference` (public) → 200 ทำงานได้โดยไม่มี token

### Edge Cases
- ผู้ใช้ใหม่ไม่เคยตั้ง profile → GET → ทุก personality field = null
- Clear field: PUT body `{"mbti": null}` → DB: NULL + history บันทึก clear event
- Partial: PUT `{"clifton_top5": []}` → ตีความเป็น clear → NULL
- Mixed: PUT `{"mbti": null, "via_top5": [...]}` → mbti cleared, via set, others คงเดิม → history 2 rows
- ความ stress: clifton_top5 = `["Achiever"]` (1 item) → 200 — รองรับ user ที่จำได้แค่บางตัว
- I18n: identity_summary ภาษาไทย + mbti = "INTJ" → format_personality_for_llm ผสม TH+EN ถูก
- Cross-system: set MBTI + Clifton แต่ Enneagram + VIA ปล่อยว่าง → MCP get_profile ส่งเฉพาะ 2 ระบบที่มี + summary มีแค่ 2 ระบบ

### History edge cases
- ผู้ใช้ใหม่ที่ไม่เคย set personality → GET history → empty list, count=0
- limit=1 → คืน entry ล่าสุดอันเดียว
- ผู้ใช้ A query history ของผู้ใช้ B → 401/404 (user-scoped)
- 100+ entries → pagination ผ่าน limit
- Concurrent updates: 2 tabs save พร้อมกัน → 2 history rows (last-write-wins; OK MVP)

### Plan Limits / Locked-data
- ไม่มี plan limit เกี่ยวข้อง — personality เก็บใน UserProfile (ไม่ใช่ File/ContextPack)
- ผู้ใช้ Free ทุกคนใช้ feature ได้ครบ ✅

### MCP Permission edge
- ผู้ใช้ disable `update_profile` → MCP เรียกถูก gate → "Tool disabled" ปกติ ✅

### Security
- SQL injection: ผ่าน SQLAlchemy parameterized ✅
- XSS: history modal render label ใช้ textContent ✅
- Cross-user history leak: ทุก query มี `where(user_id == current_user.id)` ✅
- External link: rel="noopener noreferrer" ✅

---

## ✅ Done Criteria

- [ ] DB migration รันได้บน fresh DB + DB v5.9.3 เก่า — ไม่ทำให้ user เก่าเสียหาย
- [ ] `personality_history` table สร้างได้ + index ทำงาน
- [ ] GET /api/profile คืน 4 field ใหม่ (อาจ null) — backward compatible
- [ ] PUT /api/profile รับ 4 field ใหม่ — validate ครบ — partial update ทำงาน — history append เมื่อค่าเปลี่ยน
- [ ] GET /api/personality/reference คืน reference data 4 ระบบครบ
- [ ] GET /api/profile/personality/history คืน history เรียง desc + filter ตาม system ได้
- [ ] MCP `update_profile` รับ params ใหม่ — validate ครบ — history source = "mcp_update"
- [ ] MCP `get_profile` คืน personality fields + personality_summary **พร้อมกันในการเรียกครั้งเดียว**
- [ ] Frontend modal: 4 personality blocks + history button + history modal ทำงาน
- [ ] "ไม่รู้?" links เปิด tab ใหม่ + ใช้ rel="noopener noreferrer"
- [ ] Wing dropdown enable/disable ตาม core (รวม wrap-around)
- [ ] Chat retriever inject personality block (verify ผ่าน ContextInjectionLog)
- [ ] Tests ทั้งหมด pass + coverage ≥ 80% ของโค้ดใหม่
- [ ] LLM injection: TH+EN ผสม
- [ ] No trademark violations: ไม่ copy descriptions ของ Gallup/MBTI Co.
- [ ] PDPA disclaimer ข้าง "ไม่รู้?" links
- [ ] Memory updated: api-spec.md, data-models.md, last-session.md, pipeline-state.md

---

## ⚠️ Risks

### Technical
1. **Migration บน production live volume** — Fly.io persistent volume. Migration บน startup → auto-backup เกิดก่อน. ⚠️ ถ้า crash → rollback by replacing DB with backup ใน `/app/data/backups/`
2. **Trademark ของ Gallup CliftonStrengths** — ห้าม copy descriptions เด็ดขาด
3. **16personalities ≠ MBTI** — mitigation: source field + tooltip
4. **Pydantic validator order** — wing validator อ่าน core จาก values dict → ทดสอบ
5. **partial update convention change** — `exclude_none` → `exclude_unset` กระทบ field เดิม → regression test
6. **History table growth** — append-only + dedup logic = ไม่ urgent (~100 bytes/row)

### UX
7. **Modal ยาวเกินไป** — collapsible default ปิด
8. **ผู้ใช้สับสน personality vs identity_summary** — tooltip
9. **CliftonStrengths ฟรีไม่มี** → บอกตรงๆ ใน UI + แนะนำ VIA เป็นทางเลือกฟรี

### Open Questions
**ไม่มี — Q1-Q6 ตอบครบแล้ว ✅**

### Future Stretch
- Big Five (OCEAN)
- MBTI dimension percentages
- Enneagram tritype + instinctual variants
- CliftonStrengths/VIA Full ranking
- Visualization: radar chart
- Auto-suggest preferred_output_style จาก MBTI
- Personality Match — แนะนำ context packs ที่เหมาะ
- MCP tool `get_personality_history`

---

## 📌 Notes for เขียว

### กฎที่ห้ามลืม
1. **ห้าม copy descriptions ของ MBTI/CliftonStrengths ลง UI หรือ LLM prompt** — Enneagram/VIA OK paraphrase ของเราเองเท่านั้น
2. **`PRAGMA table_info(user_profiles)`** ไม่ใช่ `users` — เคยมี migration error
3. **JSON columns** ใช้ `json.dumps(..., ensure_ascii=False)` กันอักษรไทย escape
4. **ห้าม inline SQL** — ใช้ SQLAlchemy ORM
5. **Author-Agent: เขียว (Khiao)** ทุก commit
6. **ห้าม commit `.env`, `projectkey.db`, `.jwt_secret`, `.mcp_secret`**
7. **History append ต้อง dedup** — ก่อน insert เช็คว่าค่าใหม่ != ค่าล่าสุดของระบบนั้น

### Gotchas
- **Enneagram wing wraparound**: type 9 wings = (8,1) ไม่ใช่ (8,10). type 1 wings = (9,2). ใช้ `get_enneagram_wings()` เท่านั้น
- **MBTI suffix `-A/-T`** มาเฉพาะ NERIS — ถ้า source = "official" suffix ควร = `None`
- **CliftonStrengths theme spelling**: case-sensitive! "Self-Assurance", "Woo" — ห้าม normalize
- **VIA "Appreciation of Beauty & Excellence"** มี `&` — ใช้ textContent ใน HTML กัน escape issue
- **`get_profile` MCP tool** bundle active_contexts เดิม — insert personality fields **ระหว่าง** profile fields กับ active_contexts
- **Frontend cache `/api/personality/reference`** ใน sessionStorage key `personality_ref_v1`
- **History modal** เปิดต้อง clear data เก่าก่อน fetch ใหม่ — กัน flash

### ขนาด PR ที่คาดไว้
- backend: ~800 lines (personality.py 400, profile.py 80, main.py 100, mcp_tools.py 130, database.py 30, history endpoint 60)
- frontend: ~600 lines (HTML 160, JS 380, CSS 60)
- tests: ~450 lines (ฟ้าจะเขียน)
- รวม: PR medium-large — แตก 2 commits (backend + frontend)

### Commit message format
```
feat(profile): add personality types (MBTI/Enneagram/Clifton/VIA) + history

เพิ่ม 4 ระบบบุคลิกภาพในโปรไฟล์ + เก็บประวัติทุกครั้งที่อัปเดต
+ link out ไปทำแบบทดสอบที่เว็บออฟฟิเชียล (ฟรี+เสียเงิน)
+ inject เข้า LLM context ทั้ง chat + MCP get_profile (ส่งพร้อมกัน)

- Schema: เพิ่ม 5 columns ใน user_profiles + table personality_history + idempotent migration
- API: GET/PUT /api/profile รองรับ field ใหม่
- API: GET /api/personality/reference (public)
- API: GET /api/profile/personality/history (JWT)
- MCP: update_profile + get_profile รองรับ personality + summary
- Frontend: modal section 4 blocks + searchable dropdowns + test links + history modal

Refs: plans/personality-profile.md
Author-Agent: เขียว (Khiao)
```
