"""Deploy Rich Menu to LINE (v8.0.0 Phase I).

Run after generate_line_rich_menu_image.py creates the PNG.

Steps:
1. Create rich menu structure (areas + actions) via LINE API
2. Upload menu image
3. Set as default rich menu for all users

Run: python scripts/setup_line_rich_menu.py
Requires: LINE_CHANNEL_ACCESS_TOKEN env var (or load from Fly secrets).

Idempotent: deletes any existing default menu first.
"""
from __future__ import annotations
import json
import os
import sys

# Image dimensions (must match generate_line_rich_menu_image.py)
WIDTH = 2500
HEIGHT = 1686
TILE_W = WIDTH // 3
TILE_H = HEIGHT // 2

# Rich Menu structure with 6 tile actions
RICH_MENU_DEFINITION = {
    "size": {"width": WIDTH, "height": HEIGHT},
    "selected": True,
    "name": "PDB Assistant Main Menu",
    "chatBarText": "เมนู",
    "areas": [
        # Row 1: Upload, Search, Ask AI
        {
            "bounds": {"x": 0, "y": 0, "width": TILE_W, "height": TILE_H},
            "action": {"type": "postback", "data": "action=upload_help", "displayText": "📤 วิธีส่งไฟล์"},
        },
        {
            "bounds": {"x": TILE_W, "y": 0, "width": TILE_W, "height": TILE_H},
            "action": {"type": "message", "text": "หาไฟล์"},
        },
        {
            "bounds": {"x": TILE_W * 2, "y": 0, "width": TILE_W, "height": TILE_H},
            "action": {"type": "message", "text": "/help"},
        },
        # Row 2: Library, Settings, Open Web
        {
            "bounds": {"x": 0, "y": TILE_H, "width": TILE_W, "height": TILE_H},
            "action": {"type": "message", "text": "ฉันมีกี่ไฟล์"},
        },
        {
            "bounds": {"x": TILE_W, "y": TILE_H, "width": TILE_W, "height": TILE_H},
            "action": {"type": "postback", "data": "action=settings", "displayText": "⚙️ ตั้งค่า"},
        },
        {
            "bounds": {"x": TILE_W * 2, "y": TILE_H, "width": TILE_W, "height": TILE_H},
            "action": {"type": "message", "text": "เปิดเว็บ"},
        },
    ],
}


def main():
    try:
        import httpx
    except ImportError:
        print("ERROR: httpx not installed. Run: pip install httpx", file=sys.stderr)
        sys.exit(1)

    # Load token
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not token:
        # Try loading from .env via dotenv (if available)
        try:
            from dotenv import load_dotenv
            load_dotenv()
            token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
        except ImportError:
            pass

    if not token:
        print("ERROR: LINE_CHANNEL_ACCESS_TOKEN not set.", file=sys.stderr)
        print("On Fly.io: fly ssh console -C 'env | grep LINE'", file=sys.stderr)
        print("Or run with: LINE_CHANNEL_ACCESS_TOKEN=... python scripts/setup_line_rich_menu.py", file=sys.stderr)
        sys.exit(1)

    # Locate image
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    image_path = os.path.join(repo_root, "legacy-frontend", "line-rich-menu.png")
    if not os.path.exists(image_path):
        print(f"ERROR: Image not found at {image_path}", file=sys.stderr)
        print("Run first: python scripts/generate_line_rich_menu_image.py", file=sys.stderr)
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}
    base_url = "https://api.line.me"

    # Step 1: List existing rich menus + delete defaults to start clean
    print("→ Checking existing rich menus...")
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(f"{base_url}/v2/bot/richmenu/list", headers=headers)
        if resp.status_code == 200:
            existing = resp.json().get("richmenus", [])
            print(f"  Found {len(existing)} existing menu(s)")
            for menu in existing:
                if menu.get("name") == RICH_MENU_DEFINITION["name"]:
                    rid = menu["richMenuId"]
                    print(f"  → Deleting old menu {rid}...")
                    client.delete(f"{base_url}/v2/bot/richmenu/{rid}", headers=headers)
        elif resp.status_code == 401:
            print(f"ERROR: 401 — invalid LINE_CHANNEL_ACCESS_TOKEN", file=sys.stderr)
            sys.exit(1)

        # Step 2: Create new rich menu structure
        print("→ Creating new rich menu...")
        resp = client.post(
            f"{base_url}/v2/bot/richmenu",
            headers={**headers, "Content-Type": "application/json"},
            json=RICH_MENU_DEFINITION,
        )
        if resp.status_code != 200:
            print(f"ERROR: Create failed: {resp.status_code} {resp.text}", file=sys.stderr)
            sys.exit(1)
        rich_menu_id = resp.json()["richMenuId"]
        print(f"  ✅ Created {rich_menu_id}")

        # Step 3: Upload image
        print(f"→ Uploading image ({os.path.getsize(image_path) // 1024} KB)...")
        with open(image_path, "rb") as f:
            img_data = f.read()
        resp = client.post(
            f"https://api-data.line.me/v2/bot/richmenu/{rich_menu_id}/content",
            headers={**headers, "Content-Type": "image/png"},
            content=img_data,
        )
        if resp.status_code != 200:
            print(f"ERROR: Image upload failed: {resp.status_code} {resp.text}", file=sys.stderr)
            sys.exit(1)
        print("  ✅ Image uploaded")

        # Step 4: Set as default menu
        print("→ Setting as default menu...")
        resp = client.post(
            f"{base_url}/v2/bot/user/all/richmenu/{rich_menu_id}",
            headers=headers,
        )
        if resp.status_code != 200:
            print(f"ERROR: Set default failed: {resp.status_code} {resp.text}", file=sys.stderr)
            sys.exit(1)
        print("  ✅ Default rich menu set")

    print()
    print("=" * 60)
    print("✅ Rich Menu deployed successfully!")
    print(f"   Menu ID: {rich_menu_id}")
    print(f"   Name: {RICH_MENU_DEFINITION['name']}")
    print("   All current + future bot users will see this menu")
    print()
    print("To test: open LINE app → search bot → menu should appear at bottom")


if __name__ == "__main__":
    main()
