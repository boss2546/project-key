"""Generate Rich Menu image (2500×1686 px) for LINE Bot (v8.0.0 Phase I).

Uses Pillow to draw a 6-tile (3×2) grid with PDB indigo theme + Thai labels.

Run: python scripts/generate_line_rich_menu_image.py
Output: legacy-frontend/line-rich-menu.png

Tile layout:
┌─────────────┬─────────────┬─────────────┐
│ 📤 อัพโหลด  │ 🔍 ค้นหา    │ 💬 ถาม AI   │
├─────────────┼─────────────┼─────────────┤
│ 📚 รายการ   │ ⚙️ ตั้งค่า   │ 🌐 เปิดเว็บ │
└─────────────┴─────────────┴─────────────┘
"""
from __future__ import annotations
import os
import sys

# LINE Rich Menu spec: 2500×1686 (ใหญ่) or 2500×843 (เล็ก) — ใช้ใหญ่
WIDTH = 2500
HEIGHT = 1686

# 3×2 grid → tile = 833×843 (rounded)
TILE_W = WIDTH // 3
TILE_H = HEIGHT // 2

# PDB theme colors
BG_DARK = (10, 14, 26)        # --bg-primary
SURFACE = (17, 24, 39)        # --bg-secondary
ACCENT = (99, 102, 241)       # --accent (indigo)
ACCENT_HOVER = (129, 140, 248)
TEXT_WHITE = (235, 240, 250)
TEXT_GRAY = (148, 163, 184)
LINE_GREEN = (6, 199, 85)
DIVIDER = (255, 255, 255, 18)  # 7% white

# Tile config: (icon_emoji, label_thai, label_en, accent_color)
TILES = [
    ("📤", "อัพโหลด", "Upload", (99, 102, 241)),
    ("🔍", "ค้นหา", "Search", (139, 92, 246)),  # purple
    ("💬", "ถาม AI", "Ask AI", LINE_GREEN),
    ("📚", "รายการ", "Library", (236, 72, 153)),  # pink
    ("⚙️", "ตั้งค่า", "Settings", (245, 158, 11)),  # amber
    ("🌐", "เปิดเว็บ", "Open Web", (59, 130, 246)),  # blue
]


def find_thai_font_path() -> str | None:
    """Locate a Thai-capable font. Returns None if not found."""
    candidates = [
        # Windows
        "C:/Windows/Fonts/tahoma.ttf",
        "C:/Windows/Fonts/leelawui.ttf",
        "C:/Windows/Fonts/thsarabunnew.ttf",
        # Linux
        "/usr/share/fonts/truetype/tlwg/Garuda.ttf",
        "/usr/share/fonts/truetype/tlwg/Loma.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        # macOS
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def draw_tile(draw, image, idx: int, col: int, row: int, icon: str, label_th: str, label_en: str, accent: tuple, font_label, font_sub):
    """Draw a single tile."""
    from PIL import ImageDraw  # noqa

    x0 = col * TILE_W
    y0 = row * TILE_H
    x1 = x0 + TILE_W
    y1 = y0 + TILE_H

    # Tile background — gradient via 2 rectangles (subtle)
    # Top half: surface color
    draw.rectangle([x0, y0, x1, y0 + TILE_H // 2], fill=SURFACE)
    # Bottom half: slightly lighter (accent tint at very low opacity)
    draw.rectangle([x0, y0 + TILE_H // 2, x1, y1], fill=tuple(min(255, c + 6) for c in SURFACE))

    # Tile border (thin)
    draw.rectangle([x0, y0, x1 - 1, y1 - 1], outline=(255, 255, 255, 30), width=2)

    # Icon (large, centered top half)
    cx = x0 + TILE_W // 2
    icon_y = y0 + TILE_H // 4 + 30  # roughly 1/3 from top
    # Draw icon as text (emoji)
    try:
        draw.text((cx, icon_y), icon, anchor="mm", fill=accent, font=font_label)
    except Exception:
        # Fallback if font doesn't support emoji — draw colored circle as substitute
        draw.ellipse([cx - 40, icon_y - 40, cx + 40, icon_y + 40], fill=accent)

    # Thai label (large, bottom half)
    label_y = y0 + TILE_H * 2 // 3 + 30
    try:
        draw.text((cx, label_y), label_th, anchor="mm", fill=TEXT_WHITE, font=font_label)
    except Exception:
        draw.text((cx, label_y), label_en, anchor="mm", fill=TEXT_WHITE, font=font_label)

    # English subtitle (smaller, below)
    sub_y = label_y + 80
    draw.text((cx, sub_y), label_en, anchor="mm", fill=TEXT_GRAY, font=font_sub)


def main():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("ERROR: Pillow not installed. Run: pip install Pillow", file=sys.stderr)
        sys.exit(1)

    # Create canvas
    image = Image.new("RGB", (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(image, "RGBA")

    # Load font
    font_path = find_thai_font_path()
    if font_path:
        try:
            font_label = ImageFont.truetype(font_path, 130)
            font_sub = ImageFont.truetype(font_path, 60)
        except Exception:
            font_label = ImageFont.load_default()
            font_sub = ImageFont.load_default()
    else:
        print("WARNING: No Thai font found — using default (English-only labels)", file=sys.stderr)
        font_label = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    # Draw 6 tiles (3 cols × 2 rows)
    for idx, (icon, label_th, label_en, accent) in enumerate(TILES):
        col = idx % 3
        row = idx // 3
        draw_tile(draw, image, idx, col, row, icon, label_th, label_en, accent, font_label, font_sub)

    # Draw dividers (between tiles)
    for col in range(1, 3):
        x = col * TILE_W
        draw.line([(x, 0), (x, HEIGHT)], fill=(255, 255, 255, 25), width=4)
    draw.line([(0, TILE_H), (WIDTH, TILE_H)], fill=(255, 255, 255, 25), width=4)

    # Watermark (bottom-right)
    wm = "Personal Data Bank"
    try:
        wm_font = ImageFont.truetype(font_path, 40) if font_path else font_sub
        draw.text((WIDTH - 40, HEIGHT - 30), wm, anchor="rm", fill=(255, 255, 255, 80), font=wm_font)
    except Exception:
        pass

    # Save
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_path = os.path.join(repo_root, "legacy-frontend", "line-rich-menu.png")
    # LINE requires PNG/JPEG, ≤1MB, RGB (no alpha for the saved file)
    image.save(output_path, "PNG", optimize=True)

    size_kb = os.path.getsize(output_path) / 1024
    print(f"✅ Generated: {output_path}")
    print(f"   Size: {WIDTH}×{HEIGHT} px, {size_kb:.0f} KB")
    if size_kb > 1024:
        print(f"   ⚠️ Size > 1MB — LINE may reject. Consider reducing JPG quality.")


if __name__ == "__main__":
    main()
