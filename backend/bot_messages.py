"""LINE Flex Message builders (v8.0.0).

Pure-function builders ที่รับ data → return Flex Message JSON dict.
ไม่มี side effects, ไม่ depend on DB — test ได้ ง่าย.

Used by:
- Phase E welcome flow (welcome_status_card)
- Phase F file upload confirmation (file_upload_card)
- Phase G search results (file_carousel) + stats (vault_status_card)
- Phase H error UX (error_card)

Flex JSON spec: https://developers.line.biz/en/reference/messaging-api/#flex-message
"""
from __future__ import annotations
from typing import Optional

# LINE brand color
LINE_GREEN = "#06C755"
ACCENT_INDIGO = "#6366f1"  # PDB accent
TEXT_DARK = "#1f2937"
TEXT_GRAY = "#6b7280"
TEXT_LIGHT = "#9ca3af"
BG_CARD = "#ffffff"


def link_prompt_card(link_url: str) -> dict:
    """Phase E — Card ที่ส่งให้ user หลัง follow event เพื่อขอเชื่อมบัญชี.

    User กดปุ่ม → เปิด /auth/line?linkToken=... ใน LINE in-app browser
    """
    return {
        "type": "flex",
        "altText": "เชื่อมบัญชี Personal Data Bank ของคุณก่อนเริ่มใช้",
        "contents": {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": LINE_GREEN,
                "paddingAll": "16px",
                "contents": [
                    {
                        "type": "text",
                        "text": "👋 ยินดีต้อนรับ",
                        "color": "#ffffff",
                        "size": "sm",
                        "weight": "bold",
                    },
                    {
                        "type": "text",
                        "text": "Personal Data Bank",
                        "color": "#ffffff",
                        "size": "lg",
                        "weight": "bold",
                        "margin": "xs",
                    },
                ],
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": "ผู้ช่วยจัดการข้อมูลส่วนตัวของคุณ",
                        "size": "sm",
                        "color": TEXT_DARK,
                        "wrap": True,
                    },
                    {
                        "type": "text",
                        "text": "ก่อนเริ่มใช้งาน กรุณาเชื่อมบัญชี PDB ของคุณกับ LINE นี้",
                        "size": "xs",
                        "color": TEXT_GRAY,
                        "wrap": True,
                        "margin": "md",
                    },
                ],
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": LINE_GREEN,
                        "height": "sm",
                        "action": {
                            "type": "uri",
                            "label": "🔗 เชื่อมบัญชี",
                            "uri": link_url,
                        },
                    },
                ],
            },
        },
    }


def vault_status_card(
    user_name: str,
    file_count: int,
    cluster_count: int,
    pack_count: int,
    storage_mb_used: float,
    storage_mb_limit: float,
    storage_mode: str = "managed",
    pending_organize: int = 0,
) -> dict:
    """Phase E (welcome) + Phase G (stats query) — สถานะตู้ของ user."""
    storage_label = "Google Drive (BYOS)" if storage_mode == "byos" else "Personal Data Bank"
    storage_pct = int((storage_mb_used / storage_mb_limit) * 100) if storage_mb_limit > 0 else 0

    body_contents = [
        {
            "type": "text",
            "text": f"สถานะตู้ของ {user_name}",
            "size": "sm",
            "color": TEXT_GRAY,
            "weight": "bold",
        },
        {
            "type": "separator",
            "margin": "md",
        },
        _info_row("📁 ไฟล์", str(file_count)),
        _info_row("📚 Collections", str(cluster_count)),
        _info_row("🔗 Context Packs", str(pack_count)),
        _info_row("💾 Storage", storage_label),
        _info_row(
            "📦 พื้นที่",
            f"{storage_mb_used:.0f} / {storage_mb_limit:.0f} MB ({storage_pct}%)",
        ),
    ]

    footer_contents = []
    if pending_organize > 0:
        body_contents.append(
            {
                "type": "text",
                "text": f"⚠️ ไฟล์รอจัดระเบียบ: {pending_organize}",
                "size": "xs",
                "color": "#f59e0b",
                "margin": "md",
            }
        )
        footer_contents.append(
            {
                "type": "button",
                "style": "primary",
                "color": ACCENT_INDIGO,
                "height": "sm",
                "action": {
                    "type": "postback",
                    "label": "จัดระเบียบเลย",
                    "data": "action=organize_now",
                },
            }
        )

    bubble = {
        "type": "bubble",
        "size": "kilo",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": body_contents,
        },
    }
    if footer_contents:
        bubble["footer"] = {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": footer_contents,
        }

    return {
        "type": "flex",
        "altText": f"📊 สถานะตู้: {file_count} ไฟล์, {cluster_count} collections",
        "contents": bubble,
    }


def file_upload_confirmation_card(
    file_id: str,
    filename: str,
    filetype: str,
    text_length: int,
    cluster_title: Optional[str] = None,
    download_url: Optional[str] = None,
    web_url: Optional[str] = None,
) -> dict:
    """Phase F — Card ตอบหลัง user upload ไฟล์ (organize เสร็จแล้ว)."""
    icon = _filetype_icon(filetype)
    body_contents = [
        {
            "type": "box",
            "layout": "horizontal",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": icon, "size": "xxl", "flex": 0},
                {
                    "type": "box",
                    "layout": "vertical",
                    "flex": 1,
                    "contents": [
                        {
                            "type": "text",
                            "text": filename,
                            "size": "sm",
                            "weight": "bold",
                            "color": TEXT_DARK,
                            "wrap": True,
                        },
                        {
                            "type": "text",
                            "text": f"{text_length:,} ตัวอักษร · {filetype.upper()}",
                            "size": "xs",
                            "color": TEXT_GRAY,
                            "margin": "xs",
                        },
                    ],
                },
            ],
        },
        {"type": "separator", "margin": "md"},
        {
            "type": "text",
            "text": "✅ เก็บเรียบร้อยแล้ว" if cluster_title else "📤 อัปโหลดสำเร็จ",
            "size": "sm",
            "color": LINE_GREEN if cluster_title else TEXT_GRAY,
            "weight": "bold",
            "margin": "md",
        },
    ]
    if cluster_title:
        body_contents.append(
            {
                "type": "text",
                "text": f"📚 Collection: {cluster_title}",
                "size": "xs",
                "color": TEXT_GRAY,
                "margin": "xs",
                "wrap": True,
            }
        )

    footer_contents = []
    if download_url:
        footer_contents.append(
            {
                "type": "button",
                "style": "secondary",
                "height": "sm",
                "action": {"type": "uri", "label": "📥 ดาวน์โหลด", "uri": download_url},
            }
        )
    if web_url:
        footer_contents.append(
            {
                "type": "button",
                "style": "link",
                "height": "sm",
                "action": {"type": "uri", "label": "เปิดในเว็บ", "uri": web_url},
            }
        )

    bubble = {
        "type": "bubble",
        "size": "kilo",
        "body": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": body_contents},
    }
    if footer_contents:
        bubble["footer"] = {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": footer_contents,
        }

    return {
        "type": "flex",
        "altText": f"📄 อัปโหลด '{filename}' สำเร็จ",
        "contents": bubble,
    }


def error_card(title: str, message: str, suggestion: Optional[str] = None,
               upgrade_url: Optional[str] = None) -> dict:
    """Phase H — Standard error display (plan limit / file too big / unsupported)."""
    body_contents = [
        {"type": "text", "text": "⚠️ " + title, "size": "sm", "weight": "bold", "color": "#dc2626"},
        {"type": "separator", "margin": "md"},
        {"type": "text", "text": message, "size": "sm", "color": TEXT_DARK, "wrap": True, "margin": "md"},
    ]
    if suggestion:
        body_contents.append(
            {
                "type": "text",
                "text": "💡 " + suggestion,
                "size": "xs",
                "color": TEXT_GRAY,
                "wrap": True,
                "margin": "md",
            }
        )

    footer_contents = []
    if upgrade_url:
        footer_contents.append(
            {
                "type": "button",
                "style": "primary",
                "color": ACCENT_INDIGO,
                "height": "sm",
                "action": {"type": "uri", "label": "อัปเกรด Starter", "uri": upgrade_url},
            }
        )

    bubble = {
        "type": "bubble",
        "size": "kilo",
        "body": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": body_contents},
    }
    if footer_contents:
        bubble["footer"] = {
            "type": "box",
            "layout": "vertical",
            "contents": footer_contents,
        }
    return {"type": "flex", "altText": f"⚠️ {title}", "contents": bubble}


def file_search_carousel(results: list[dict]) -> dict:
    """Phase G — Carousel ของผลลัพธ์ search (max 10 cards)."""
    bubbles = []
    for r in results[:10]:
        bubbles.append(_file_search_bubble(r))

    if not bubbles:
        return {
            "type": "flex",
            "altText": "ไม่พบไฟล์ที่ตรงกับคำค้น",
            "contents": {
                "type": "bubble",
                "size": "kilo",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": "🔍 ไม่พบไฟล์", "size": "sm", "weight": "bold"},
                        {
                            "type": "text",
                            "text": "ลอง keyword อื่น หรือ upload ไฟล์ใหม่ก่อน",
                            "size": "xs",
                            "color": TEXT_GRAY,
                            "margin": "md",
                            "wrap": True,
                        },
                    ],
                },
            },
        }

    return {
        "type": "flex",
        "altText": f"🔍 พบ {len(bubbles)} ไฟล์",
        "contents": {"type": "carousel", "contents": bubbles},
    }


def _file_search_bubble(result: dict) -> dict:
    """One file in search carousel."""
    filename = result.get("filename", "Unknown")
    snippet = result.get("snippet") or result.get("summary") or ""
    if len(snippet) > 80:
        snippet = snippet[:77] + "..."
    score = result.get("score")
    file_id = result.get("file_id") or result.get("id", "")
    icon = _filetype_icon(result.get("filetype", ""))

    body_contents = [
        {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": [
                {"type": "text", "text": icon, "size": "xl", "flex": 0},
                {
                    "type": "text",
                    "text": filename,
                    "size": "sm",
                    "weight": "bold",
                    "color": TEXT_DARK,
                    "wrap": True,
                    "flex": 1,
                },
            ],
        }
    ]
    if snippet:
        body_contents.append(
            {
                "type": "text",
                "text": snippet,
                "size": "xxs",
                "color": TEXT_GRAY,
                "margin": "md",
                "wrap": True,
                "maxLines": 3,
            }
        )
    if score is not None:
        body_contents.append(
            {
                "type": "text",
                "text": f"Match: {score:.0%}" if isinstance(score, float) and score <= 1 else f"Match: {score}",
                "size": "xxs",
                "color": TEXT_LIGHT,
                "margin": "sm",
            }
        )

    footer_contents = [
        {
            "type": "button",
            "style": "secondary",
            "height": "sm",
            "action": {
                "type": "postback",
                "label": "เปิดดู",
                "data": f"action=open_file&file_id={file_id}",
            },
        }
    ]

    return {
        "type": "bubble",
        "size": "micro",
        "body": {"type": "box", "layout": "vertical", "spacing": "xs", "contents": body_contents},
        "footer": {"type": "box", "layout": "vertical", "spacing": "xs", "contents": footer_contents},
    }


def text_with_quick_replies(text: str, quick_replies: list[dict]) -> list[dict]:
    """Build a text message + quick reply chips (returned as 1 message dict for messaging API).

    Each quick_replies dict: {"label": str, "data": str (postback) | "text": str (postback text)}
    Max 13 chips per LINE spec.
    """
    items = []
    for qr in quick_replies[:13]:
        action: dict
        if "data" in qr:
            action = {"type": "postback", "label": qr["label"], "data": qr["data"]}
        else:
            action = {"type": "message", "label": qr["label"], "text": qr.get("text", qr["label"])}
        items.append({"type": "action", "action": action})

    return [{
        "type": "text",
        "text": text,
        "quickReply": {"items": items} if items else None,
    }]


# ─── Helpers ───
def _info_row(label: str, value: str) -> dict:
    """Horizontal label/value row."""
    return {
        "type": "box",
        "layout": "horizontal",
        "contents": [
            {"type": "text", "text": label, "size": "xs", "color": TEXT_GRAY, "flex": 2},
            {
                "type": "text",
                "text": value,
                "size": "xs",
                "color": TEXT_DARK,
                "weight": "bold",
                "flex": 3,
                "align": "end",
                "wrap": True,
            },
        ],
    }


_FILETYPE_ICONS = {
    "pdf": "📕",
    "docx": "📘",
    "doc": "📘",
    "txt": "📄",
    "md": "📝",
    "csv": "📊",
    "xlsx": "📊",
    "xls": "📊",
    "pptx": "📑",
    "ppt": "📑",
    "html": "🌐",
    "json": "🧾",
    "rtf": "📄",
    "png": "🖼️",
    "jpg": "🖼️",
    "jpeg": "🖼️",
    "webp": "🖼️",
    "mp3": "🎵",
    "m4a": "🎵",
    "mp4": "🎬",
}


def _filetype_icon(filetype: str) -> str:
    return _FILETYPE_ICONS.get((filetype or "").lower(), "📄")
