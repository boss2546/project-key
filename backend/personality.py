"""Personality reference data + validators + LLM helpers — v6.0.

ครอบคลุม 4 ระบบ: MBTI / Enneagram / CliftonStrengths / VIA Character Strengths.

⚠️ Trademark / Licensing constraints:
- MBTI® (The Myers-Briggs Company) — เก็บค่าผู้ใช้กรอกเอง + link out เท่านั้น
- CliftonStrengths® (Gallup) — ห้าม copy descriptions ลง UI/LLM ส่งแค่ชื่อ theme
- Enneagram = public domain (paraphrase TH/EN ของเราเองได้)
- VIA = official ฟรี + เปิดให้ใช้ส่วนตัว (paraphrase ได้)

ห้าม inline modulo สำหรับ Enneagram wing — ใช้ get_enneagram_wings() เท่านั้น
เพื่อกัน off-by-one error ของการ wrap (type 9 wings = 8,1 ไม่ใช่ 8,10)
"""
from __future__ import annotations


# ═══════════════════════════════════════════
# 1. MBTI — 16 types + 3 sources + 2 test links
# ═══════════════════════════════════════════

MBTI_TYPES: list[str] = [
    "ISTJ", "ISFJ", "INFJ", "INTJ",
    "ISTP", "ISFP", "INFP", "INTP",
    "ESTP", "ESFP", "ENFP", "ENTP",
    "ESTJ", "ESFJ", "ENFJ", "ENTJ",
]

# source = ที่มาของผลทดสอบ — แยกเพราะ NERIS (16personalities) ไม่ใช่ MBTI® official
MBTI_SOURCES: list[str] = ["official", "neris", "self_report"]

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


# ═══════════════════════════════════════════
# 2. ENNEAGRAM — 9 types (TH+EN) + 3 test links
# ═══════════════════════════════════════════

# คำอธิบายไทย/อังกฤษเป็นชื่อกลางที่ใช้ทั่วไป — public domain
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


# ═══════════════════════════════════════════
# 3. CLIFTONSTRENGTHS — 34 themes / 4 domains + 2 test links
# ═══════════════════════════════════════════

# ⚠️ Spelling case-sensitive — ห้าม normalize "Self-Assurance", "Woo"
# Gallup ถือลิขสิทธิ์ definitions → ห้าม copy descriptions ที่นี่ (ส่งแค่ชื่อให้ LLM)
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

# Flatten ตามลำดับ — ใช้สำหรับ validate
CLIFTON_ALL_THEMES: list[str] = sum(CLIFTON_THEMES.values(), [])

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


# ═══════════════════════════════════════════
# 4. VIA CHARACTER STRENGTHS — 24 strengths / 6 virtues + 1 free official test link
# ═══════════════════════════════════════════

# ⚠️ "Appreciation of Beauty & Excellence" มี & — ใน HTML ใช้ textContent กัน escape issue
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

VIA_TEST_LINKS: list[dict] = [
    {
        "name": "VIA Institute (ฟรี — official)",
        "url": "https://www.viacharacter.org/",
        "cost": "free",
        "note": "official + ฟรี + แนะนำที่สุด",
    },
]


# ═══════════════════════════════════════════
# 5. VALIDATION HELPERS
# ═══════════════════════════════════════════

def validate_mbti(value: str) -> bool:
    """รองรับ "INTJ" / "INTJ-A" / "INTJ-T".

    -A/-T มาจาก NERIS (16personalities) เท่านั้น — official MBTI ไม่มี suffix
    Validation ขั้น service จะเช็ค consistency อีกชั้น
    """
    if not value or not isinstance(value, str):
        return False
    parts = value.split("-")
    if len(parts) > 2:
        return False
    base = parts[0]
    suffix = parts[1] if len(parts) == 2 else None
    return base in MBTI_TYPES and (suffix is None or suffix in ("A", "T"))


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


def validate_enneagram(core: int, wing: int | None) -> bool:
    """core ต้องอยู่ 1-9, wing ต้องเป็น ±1 ของ core (รวม wrap-around)."""
    if not isinstance(core, int) or not (1 <= core <= 9):
        return False
    if wing is None:
        return True
    if not isinstance(wing, int):
        return False
    return wing in get_enneagram_wings(core)


def validate_clifton(themes: list[str]) -> tuple[bool, list[str]]:
    """คืน (is_valid, list_of_offending_themes_or_codes).

    Codes:
        ["TOO_MANY"]   — ถ้า > 5 items
        ["DUPLICATE"]  — ถ้ามีซ้ำ
        ["X", "Y"]     — list ของ theme ที่ไม่ valid
    """
    if not isinstance(themes, list):
        return (False, ["NOT_LIST"])
    if len(themes) > 5:
        return (False, ["TOO_MANY"])
    if len(set(themes)) != len(themes):
        return (False, ["DUPLICATE"])
    invalid = [t for t in themes if t not in CLIFTON_ALL_THEMES]
    return (len(invalid) == 0, invalid)


def validate_via(strengths: list[str]) -> tuple[bool, list[str]]:
    """เหมือน validate_clifton แต่เทียบกับ VIA_ALL_STRENGTHS (24 ค่า)."""
    if not isinstance(strengths, list):
        return (False, ["NOT_LIST"])
    if len(strengths) > 5:
        return (False, ["TOO_MANY"])
    if len(set(strengths)) != len(strengths):
        return (False, ["DUPLICATE"])
    invalid = [s for s in strengths if s not in VIA_ALL_STRENGTHS]
    return (len(invalid) == 0, invalid)


# ═══════════════════════════════════════════
# 6. LLM-INJECTION HELPERS — TH+EN ผสม (per Q5)
# ═══════════════════════════════════════════

def format_personality_for_llm(profile: dict) -> str:
    """สร้าง text block "PERSONALITY PROFILE" สำหรับ inject เข้า LLM context.

    คืน "" ถ้าผู้ใช้ยังไม่ตั้งบุคลิกภาพระบบใดเลย — caller จะข้าม (ไม่ inject ส่วนเปล่า)

    ⚠️ ห้าม copy descriptions ของ MBTI/Clifton — ส่งแค่ชื่อ + paraphrase Enneagram TH/EN เท่านั้น
    """
    if not profile:
        return ""

    parts: list[str] = []

    mbti = profile.get("mbti")
    if mbti and isinstance(mbti, dict) and mbti.get("type"):
        src = mbti.get("source") or "self_report"
        parts.append(f"MBTI: {mbti['type']} (source: {src})")

    enneagram = profile.get("enneagram")
    if enneagram and isinstance(enneagram, dict) and enneagram.get("core"):
        wing = enneagram.get("wing")
        wing_str = f"w{wing}" if wing else ""
        type_info = ENNEAGRAM_TYPES.get(enneagram["core"], {})
        type_th = type_info.get("th", "")
        type_en = type_info.get("en", "")
        parts.append(f"Enneagram: {enneagram['core']}{wing_str} ({type_th} / {type_en})")

    clifton_top5 = profile.get("clifton_top5")
    if clifton_top5 and isinstance(clifton_top5, list):
        parts.append(f"จุดแข็งงาน CliftonStrengths Top 5: {', '.join(clifton_top5)}")

    via_top5 = profile.get("via_top5")
    if via_top5 and isinstance(via_top5, list):
        parts.append(f"คุณค่าหลัก VIA Top 5: {', '.join(via_top5)}")

    if not parts:
        return ""

    return "=== PERSONALITY PROFILE ===\n" + "\n".join(parts) + "\n=== END PERSONALITY ==="


def build_personality_summary(profile: dict) -> str:
    """สร้างบรรทัดสรุปบุคลิก 1 บรรทัด สำหรับ MCP get_profile.

    AI ภายนอก (Claude/Antigravity/ChatGPT) ใช้ได้ทันทีโดยไม่ต้อง parse โครงสร้าง 4 ระบบ
    Format: "INTJ-A | Enneagram 5w4 | Clifton: A + B + C | VIA: X + Y"
    คืน "" ถ้าไม่มีข้อมูลเลย
    """
    if not profile:
        return ""

    bits: list[str] = []

    mbti = profile.get("mbti")
    if mbti and isinstance(mbti, dict) and mbti.get("type"):
        bits.append(mbti["type"])

    enneagram = profile.get("enneagram")
    if enneagram and isinstance(enneagram, dict) and enneagram.get("core"):
        wing = enneagram.get("wing")
        wing_str = f"w{wing}" if wing else ""
        bits.append(f"Enneagram {enneagram['core']}{wing_str}")

    clifton_top5 = profile.get("clifton_top5")
    if clifton_top5 and isinstance(clifton_top5, list):
        # โชว์ top 3 เพื่อให้ summary สั้น
        top3 = " + ".join(clifton_top5[:3])
        bits.append(f"Clifton: {top3}")

    via_top5 = profile.get("via_top5")
    if via_top5 and isinstance(via_top5, list):
        # โชว์ top 2 เพื่อให้ summary สั้น
        top2 = " + ".join(via_top5[:2])
        bits.append(f"VIA: {top2}")

    return " | ".join(bits)


# ═══════════════════════════════════════════
# 7. PUBLIC ACCESSOR — ใช้โดย /api/personality/reference endpoint
# ═══════════════════════════════════════════

def get_test_links(system: str) -> list[dict]:
    """คืน test_links ของระบบที่ระบุ — สำหรับ frontend ใช้ผ่าน /api/personality/reference."""
    links_map = {
        "mbti": MBTI_TEST_LINKS,
        "enneagram": ENNEAGRAM_TEST_LINKS,
        "clifton": CLIFTON_TEST_LINKS,
        "via": VIA_TEST_LINKS,
    }
    return links_map.get(system, [])


# ระบบทั้งหมดที่ valid (ใช้ check ใน history endpoint)
SUPPORTED_SYSTEMS: list[str] = ["mbti", "enneagram", "clifton", "via"]
