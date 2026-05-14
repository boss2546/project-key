# 02 — Personality System Data (Verbatim)

> **Purpose:** Exact data ของ 4 personality systems ที่ PDB รองรับ (MBTI / Enneagram / CliftonStrengths / VIA)
> **Why:** ใช้สำหรับ profile UI + history audit + LLM context injection — copy paste โดยตรงได้
> **Source:** [backend/personality.py](../../backend/personality.py)

---

## ภาพรวม 4 ระบบ

| System | Owner | License | Storage Field | Max Items |
|---|---|---|---|---|
| **MBTI®** | The Myers-Briggs Company | Trademark — store user values only, link to official tests | `user_profiles["mbti"]` | 1 type |
| **Enneagram** | Public Domain | Paraphrase Thai/English allowed | `user_profiles["enneagram"]` | 1 core + optional wing |
| **CliftonStrengths®** | Gallup | Trademark — **NO descriptions in UI/LLM** — names only | `user_profiles["clifton_top5"]` | Top 5 |
| **VIA Character Strengths** | VIA Institute (Public Domain) | Free + open; paraphrase allowed | `user_profiles["via_top5"]` | Top 5 |

**Supported systems constant:**
```python
SUPPORTED_SYSTEMS: list[str] = ["mbti", "enneagram", "clifton", "via"]
```

---

## 1. MBTI System

### 16 Types (verbatim)
```python
MBTI_TYPES: list[str] = [
    "ISTJ", "ISFJ", "INFJ", "INTJ",
    "ISTP", "ISFP", "INFP", "INTP",
    "ESTP", "ESFP", "ENFP", "ENTP",
    "ESTJ", "ESFJ", "ENFJ", "ENTJ",
]
```

### Sources
```python
MBTI_SOURCES: list[str] = ["official", "neris", "self_report"]
```

| Source | Meaning | Suffix? |
|---|---|---|
| `official` | mbtionline.com paid test | No suffix |
| `neris` | 16personalities.com (NERIS Type Explorer) | `-A` Assertive or `-T` Turbulent |
| `self_report` | User self-identified | No suffix |

### Test Links
```python
MBTI_TEST_LINKS: list[dict] = [
    {
        "name": "16personalities (ฟรี)",
        "url": "https://www.16personalities.com/",
        "cost": "free",
        "note": "ใช้ NERIS Type Explorer — คล้าย MBTI แต่ไม่ใช่ official",
    },
    {
        "name": "MBTI Online (Official)",
        "url": "https://www.mbtionline.com/",
        "cost": "$50 USD",
        "note": "ของบริษัทเจ้าของลิขสิทธิ์ MBTI",
    },
]
```

### Validation
```python
def validate_mbti(value: str) -> bool:
    """รองรับ "INTJ" / "INTJ-A" / "INTJ-T"."""
    if not value or not isinstance(value, str):
        return False
    parts = value.split("-")
    if len(parts) > 2:
        return False
    base = parts[0]
    suffix = parts[1] if len(parts) == 2 else None
    return base in MBTI_TYPES and (suffix is None or suffix in ("A", "T"))
```

**Valid examples:** `"INTJ"`, `"INTJ-A"`, `"INTJ-T"`
**Invalid examples:** `"INTJ-X"`, `"ABCD"`, `"intj"` (lowercase), `""`

### Storage shape
```python
user_profiles["mbti"] = {
    "type": "INTJ-A",      # 16 types + optional NERIS suffix
    "source": "neris"      # one of MBTI_SOURCES
}
```

---

## 2. Enneagram System

### 9 Types (Thai + English)
```python
ENNEAGRAM_TYPES: dict[int, dict[str, str]] = {
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
```

### Test Links
```python
ENNEAGRAM_TEST_LINKS: list[dict] = [
    {
        "name": "Truity (ฟรี)",
        "url": "https://www.truity.com/test/enneagram-personality-test",
        "cost": "free",
    },
    {
        "name": "Eclectic Energies (ฟรี, ไม่ต้องใช้อีเมล)",
        "url": "https://www.eclecticenergies.com/enneagram/test",
        "cost": "free",
    },
    {
        "name": "Enneagram Institute RHETI",
        "url": "https://www.enneagraminstitute.com/",
        "cost": "$12 USD",
    },
]
```

### Wing Logic — ⚠️ CRITICAL: ห้ามใช้ modulo inline

```python
def get_enneagram_wings(core: int) -> tuple[int, int]:
    """คืน wings 2 ค่าที่ valid (left, right) พร้อม wrap-around.

    Examples:
        core=4 → (3, 5)
        core=9 → (8, 1)   # wrap — wing 10 ไม่มี
        core=1 → (9, 2)   # wrap — wing 0 ไม่มี
    """
    if not isinstance(core, int) or not (1 <= core <= 9):
        raise ValueError(f"Invalid Enneagram core: {core}")
    left = core - 1 if core > 1 else 9
    right = core + 1 if core < 9 else 1
    return (left, right)
```

**ทำไม CRITICAL:** Type 9 wings = (8, 1) ไม่ใช่ (8, 10) — modulo arithmetic จะ off-by-one

### Validation
```python
def validate_enneagram(core: int, wing: int | None) -> bool:
    """core ต้องอยู่ 1-9, wing ต้องเป็น ±1 ของ core (รวม wrap-around)."""
    if not isinstance(core, int) or not (1 <= core <= 9):
        return False
    if wing is None:
        return True
    if not isinstance(wing, int):
        return False
    return wing in get_enneagram_wings(core)
```

### Storage shape
```python
user_profiles["enneagram"] = {
    "core": 5,      # int 1-9 required
    "wing": 4       # int ±1 of core (with wrap), or None (no wing)
}
# Display format: "5w4" (or just "5" if no wing)
```

---

## 3. CliftonStrengths System (Gallup) ®

### 34 Themes — 4 Domains
```python
CLIFTON_THEMES: dict[str, list[str]] = {
    "executing": [
        "Achiever", "Arranger", "Belief", "Consistency", "Deliberative",
        "Discipline", "Focus", "Responsibility", "Restorative",
    ],
    "influencing": [
        "Activator", "Command", "Communication", "Competition",
        "Maximizer", "Self-Assurance", "Significance", "Woo",
    ],
    "relationship_building": [
        "Adaptability", "Connectedness", "Developer", "Empathy",
        "Harmony", "Includer", "Individualization", "Positivity", "Relator",
    ],
    "strategic_thinking": [
        "Analytical", "Context", "Futuristic", "Ideation", "Input",
        "Intellection", "Learner", "Strategic",
    ],
}

CLIFTON_ALL_THEMES: list[str] = sum(CLIFTON_THEMES.values(), [])
```

**Total = 34 themes:** 9 executing + 8 influencing + 9 relationship_building + 8 strategic_thinking

### Test Links
```python
CLIFTON_TEST_LINKS: list[dict] = [
    {
        "name": "Gallup CliftonStrengths Top 5",
        "url": "https://www.gallup.com/cliftonstrengths/en/home.aspx",
        "cost": "$24.99 USD",
        "note": "Gallup เป็นเว็บเดียวที่ official — ไม่มีเวอร์ชันฟรี",
    },
    {
        "name": "Gallup CliftonStrengths Full 34",
        "url": "https://www.gallup.com/cliftonstrengths/en/home.aspx",
        "cost": "$59.99 USD",
    },
]
```

### Validation
```python
def validate_clifton(themes: list[str]) -> tuple[bool, list[str]]:
    """คืน (is_valid, list_of_offending_themes_or_codes)."""
    if not isinstance(themes, list):
        return (False, ["NOT_LIST"])
    if len(themes) > 5:
        return (False, ["TOO_MANY"])
    if len(set(themes)) != len(themes):
        return (False, ["DUPLICATE"])
    invalid = [t for t in themes if t not in CLIFTON_ALL_THEMES]
    return (len(invalid) == 0, invalid)
```

**Error codes:**
- `["NOT_LIST"]` — input ไม่ใช่ list
- `["TOO_MANY"]` — เกิน 5 items
- `["DUPLICATE"]` — มี theme ซ้ำ
- `["X", "Y", ...]` — list of invalid theme names

### ⚠️ Trademark Constraint
**ห้าม copy theme descriptions ไป UI/LLM** — ส่งแค่ theme names เท่านั้น
**Case-sensitive exact strings:** `"Self-Assurance"` (มี `-`), `"Woo"` (3 chars)

### Storage shape
```python
user_profiles["clifton_top5"] = ["Achiever", "Analytical", "Input", "Learner", "Strategic"]
# Max 5, no duplicates
```

---

## 4. VIA Character Strengths

### 24 Strengths — 6 Virtues
```python
VIA_STRENGTHS: dict[str, list[str]] = {
    "wisdom": ["Creativity", "Curiosity", "Judgment", "Love of Learning", "Perspective"],
    "courage": ["Bravery", "Perseverance", "Honesty", "Zest"],
    "humanity": ["Love", "Kindness", "Social Intelligence"],
    "justice": ["Teamwork", "Fairness", "Leadership"],
    "temperance": ["Forgiveness", "Humility", "Prudence", "Self-Regulation"],
    "transcendence": [
        "Appreciation of Beauty & Excellence", "Gratitude", "Hope",
        "Humor", "Spirituality",
    ],
}

VIA_ALL_STRENGTHS: list[str] = sum(VIA_STRENGTHS.values(), [])
```

**Total = 24 strengths:** 5 wisdom + 4 courage + 3 humanity + 3 justice + 4 temperance + 5 transcendence

### Test Links
```python
VIA_TEST_LINKS: list[dict] = [
    {
        "name": "VIA Institute (ฟรี — official)",
        "url": "https://www.viacharacter.org/",
        "cost": "free",
        "note": "official + ฟรี + แนะนำที่สุด",
    },
]
```

### Validation
```python
def validate_via(strengths: list[str]) -> tuple[bool, list[str]]:
    """เหมือน validate_clifton แต่เทียบกับ VIA_ALL_STRENGTHS."""
    if not isinstance(strengths, list):
        return (False, ["NOT_LIST"])
    if len(strengths) > 5:
        return (False, ["TOO_MANY"])
    if len(set(strengths)) != len(strengths):
        return (False, ["DUPLICATE"])
    invalid = [s for s in strengths if s not in VIA_ALL_STRENGTHS]
    return (len(invalid) == 0, invalid)
```

### ⚠️ HTML Encoding Note
Strength `"Appreciation of Beauty & Excellence"` มี `&` → ใช้ `textContent` ใน HTML (ไม่ใช่ `innerHTML`) เพื่อหลีกเลี่ยง escaping issue

### Storage shape
```python
user_profiles["via_top5"] = ["Creativity", "Curiosity", "Kindness", "Hope", "Humor"]
# Max 5, no duplicates
```

---

## LLM Integration Helpers

### Format สำหรับ LLM Context Injection
```python
def format_personality_for_llm(profile: dict) -> str:
    """สร้าง text block "PERSONALITY PROFILE" สำหรับ inject เข้า LLM context."""
    # Returns:
    # === PERSONALITY PROFILE ===
    # MBTI: INTJ (source: self_report)
    # Enneagram: 5w4 (นักสำรวจ / The Investigator)
    # จุดแข็งงาน CliftonStrengths Top 5: Achiever, Analytical, ...
    # คุณค่าหลัก VIA Top 5: Creativity, Curiosity, ...
    # === END PERSONALITY ===
```

**Rules:**
- ห้าม copy MBTI/Clifton descriptions
- ส่งแค่: type names + paraphrased Enneagram TH/EN
- คืน `""` ถ้าไม่มีข้อมูลเลย → caller ข้าม injection

### One-liner Summary (for MCP `get_profile`)
```python
def build_personality_summary(profile: dict) -> str:
    """สร้างบรรทัดสรุปบุคลิก 1 บรรทัด."""
    # Returns:
    # "INTJ-A | Enneagram 5w4 | Clifton: Achiever + Analytical + Input | VIA: Creativity + Curiosity"
```

**Why:** AI ภายนอก (Claude/Antigravity/ChatGPT) ใช้ได้ทันทีโดยไม่ต้อง parse โครงสร้าง 4 ระบบ

### Reference Data Access
```python
def get_test_links(system: str) -> list[dict]:
    """คืน test_links ของระบบที่ระบุ — สำหรับ frontend ใช้ผ่าน /api/personality/reference."""
    links_map = {
        "mbti": MBTI_TEST_LINKS,
        "enneagram": ENNEAGRAM_TEST_LINKS,
        "clifton": CLIFTON_TEST_LINKS,
        "via": VIA_TEST_LINKS,
    }
    return links_map.get(system, [])
```

---

## Complete User Profile Schema

```python
{
    "mbti": {
        "type": "INTJ" | "INTJ-A" | "INTJ-T",
        "source": "official" | "neris" | "self_report"
    },
    "enneagram": {
        "core": 1-9,
        "wing": 1-9 | None  # must be ±1 of core (with wrap)
    },
    "clifton_top5": [str, ...],  # 0-5 themes from CLIFTON_ALL_THEMES, no duplicates
    "via_top5": [str, ...]       # 0-5 strengths from VIA_ALL_STRENGTHS, no duplicates
}
```

---

## Critical Implementation Checklist

- [ ] Enneagram wings: **ALWAYS** call `get_enneagram_wings(core)` — never inline modulo
- [ ] CliftonStrengths case sensitivity: `"Self-Assurance"`, `"Woo"` (exact, no normalization)
- [ ] VIA HTML encoding: use `textContent` for `"Appreciation of Beauty & Excellence"`
- [ ] LLM injection: NEVER send MBTI/Clifton descriptions (trademark)
- [ ] Validators return `(bool, list)` tuples for detailed error reporting
- [ ] Personality history: tracked in `personality_history` table (append-only) when fields change — source = `web` | `mcp_update` | `api`
- [ ] Public reference endpoint `/api/personality/reference` returns ALL 4 systems' types + test_links (no auth required)
- [ ] Top 5 ranking: ORDER MATTERS — first item = strongest. UI must preserve order, not sort.

---

**End — All data verbatim from [backend/personality.py](../../backend/personality.py)**
