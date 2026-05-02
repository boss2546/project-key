"""Tiny static file server for v7.5.0 standalone Playwright tests.

Maps /legacy/* requests to legacy-frontend/*. Other paths (e.g. /api/*) get
mocked by Playwright's page.route() — they don't reach this server.

Spawned automatically by playwright.config.standalone.js webServer config.
Manual run: python tests/e2e-ui/_static_server.py
Listens on http://127.0.0.1:8765
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND = ROOT / "legacy-frontend"
PORT = 8765

CT_BY_EXT = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml",
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]  # strip query string
        if path.startswith("/legacy/"):
            rel = path[len("/legacy/"):]
        elif path == "/" or path == "":
            rel = "app.html"
        else:
            rel = path.lstrip("/")
        target = FRONTEND / rel
        if not target.exists() or not target.is_file():
            self.send_response(404)
            self.end_headers()
            self.wfile.write(f"Not found: {rel}".encode())
            return
        ct = CT_BY_EXT.get(target.suffix.lower(), "application/octet-stream")
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        if "404" in (fmt % args):
            sys.stderr.write(f"[static] {fmt % args}\n")


if __name__ == "__main__":
    print(f"[static] serving {FRONTEND} on http://127.0.0.1:{PORT}", flush=True)
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
