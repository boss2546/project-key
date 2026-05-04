"""Configuration for Personal Data Bank (PDB) backend."""
import os
import secrets
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ─── App Version (single source of truth) ───
# Bump this when releasing. All version strings exposed to clients
# (Swagger /docs, /api/mcp/info, MCP serverInfo) read from here.
APP_VERSION = "8.0.0"

# OpenRouter API
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
LLM_MODEL = "google/gemini-3-flash-preview"            # Chat & lightweight tasks (fast, cheap)
LLM_MODEL_PRO = "google/gemini-3-flash-preview"          # ⚡ TEMP: ใช้ Flash แทน Pro เพื่อเทสเร็ว (เดิม: google/gemini-3.1-pro-preview)

# Limits
MAX_FILE_SIZE_MB = 10  # legacy — superseded by plan_limits.max_file_size_mb (per-plan)

# v7.5.0 — Big File map-reduce threshold (chars in extracted_text, not file size)
# Files where extracted_text exceeds this trigger chunking + map-reduce summary
# (raw file is preserved unchanged regardless of size).
LARGE_FILE_THRESHOLD = 30_000

# v7.5.0 — Hard upper cap on raw file size (bytes). Even with plan_limits set
# higher, this guards against memory blowup at extraction time. Adjust as
# Fly.io machine RAM allows (1024MB → 200MB safe; 2048MB → 400MB).
ABSOLUTE_MAX_FILE_SIZE_MB = 200

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# DATA_DIR: use mounted volume if available (Fly.io), else local
DATA_DIR = os.getenv("DATA_DIR", BASE_DIR)
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
CONTEXT_PACKS_DIR = os.path.join(DATA_DIR, "context_packs")
SUMMARIES_DIR = os.path.join(DATA_DIR, "summaries")
DATABASE_URL = f"sqlite+aiosqlite:///{os.path.join(DATA_DIR, 'projectkey.db')}"

# Create dirs
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CONTEXT_PACKS_DIR, exist_ok=True)
os.makedirs(SUMMARIES_DIR, exist_ok=True)

# ─── JWT Authentication (v5.0) ───
def _generate_jwt_secret() -> str:
    """Generate and persist a JWT secret key."""
    jwt_file = os.path.join(DATA_DIR, ".jwt_secret")
    if os.path.exists(jwt_file):
        with open(jwt_file, "r") as f:
            return f.read().strip()
    secret = secrets.token_urlsafe(64)
    with open(jwt_file, "w") as f:
        f.write(secret)
    return secret

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", _generate_jwt_secret())
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24 hours default

# ─── Admin Password (from env — fail closed if unset) ───
# Used as override for disabled MCP tools. Default "1234" was guessable; now required.
# Local dev: set ADMIN_PASSWORD in .env. Production: `fly secrets set ADMIN_PASSWORD=...`
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
if not ADMIN_PASSWORD:
    import sys
    print(
        "FATAL: ADMIN_PASSWORD env var is required (no default). "
        "Set in .env locally or via `fly secrets set ADMIN_PASSWORD=...` in production.",
        file=sys.stderr,
    )
    sys.exit(1)

# MCP Secret — persists across restarts
_MCP_SECRET_FILE = os.path.join(DATA_DIR, ".mcp_secret")

def _load_or_create_mcp_secret() -> str:
    """Load existing MCP secret or generate a new one."""
    if os.path.exists(_MCP_SECRET_FILE):
        with open(_MCP_SECRET_FILE, "r") as f:
            return f.read().strip()
    secret = secrets.token_urlsafe(32)
    with open(_MCP_SECRET_FILE, "w") as f:
        f.write(secret)
    return secret

MCP_SECRET = os.getenv("MCP_SECRET", _load_or_create_mcp_secret())

# ─── Stripe Payment (v5.9.2) ───
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_STARTER_PRICE_ID = os.getenv("STRIPE_STARTER_PRICE_ID", "")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")

# ─── Google Drive BYOS (v7.0.0) ───
# OAuth 2.0 credentials จาก Google Cloud Console. ถ้าว่าง = BYOS feature ปิด
# (endpoints จะ return 503 GOOGLE_OAUTH_NOT_CONFIGURED) — ไม่ break Managed Mode
GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_OAUTH_REDIRECT_URI = os.getenv(
    "GOOGLE_OAUTH_REDIRECT_URI",
    f"{APP_BASE_URL}/api/drive/oauth/callback",
)
# Picker SDK credentials (separate from OAuth — for client-side file selection)
GOOGLE_PICKER_API_KEY = os.getenv("GOOGLE_PICKER_API_KEY", "")
GOOGLE_PICKER_APP_ID = os.getenv("GOOGLE_PICKER_APP_ID", "")  # = Cloud project number

# OAuth mode: "testing" (free, 7-day token expiry, max 100 test users)
# vs "production" (verified, persistent tokens, public)
GOOGLE_OAUTH_MODE = os.getenv("GOOGLE_OAUTH_MODE", "testing")

# Fernet encryption key สำหรับ refresh_token at rest (Drive's Connection table)
# Generate ครั้งเดียวด้วย:  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# ถ้าว่าง: BYOS endpoints จะ return 503 (เก็บ token ไม่ปลอดภัยถ้าไม่ encrypt)
DRIVE_TOKEN_ENCRYPTION_KEY = os.getenv("DRIVE_TOKEN_ENCRYPTION_KEY", "")


def is_byos_configured() -> bool:
    """True ถ้า config ครบสำหรับ BYOS feature ใช้งานจริง.

    เรียกที่ endpoint level เพื่อ short-circuit เป็น 503 ถ้า env vars ยังไม่ set —
    BYOS feature จะ "ปิดเงียบๆ" จนกว่า user จะ deploy ด้วย credentials ครบ
    """
    return bool(
        GOOGLE_OAUTH_CLIENT_ID
        and GOOGLE_OAUTH_CLIENT_SECRET
        and DRIVE_TOKEN_ENCRYPTION_KEY
    )


# ─── Email Service (v7.6.0) ───
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
EMAIL_FROM_ADDRESS = os.getenv("EMAIL_FROM_ADDRESS", "noreply@personaldatabank.fly.dev")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Personal Data Bank")

def is_email_configured() -> bool:
    """True if Resend API key is configured."""
    return bool(RESEND_API_KEY)


# ─── LINE Bot Integration (v8.0.0) ───
# ทั้งหมด optional — ถ้าว่าง = LINE bot ปิดเงียบๆ (POST /webhook/line return 503)
# LINE Login channel = แยกจาก Messaging API channel — ต้อง 2 channel ใน Provider เดียวกัน
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_LOGIN_CHANNEL_ID = os.getenv("LINE_LOGIN_CHANNEL_ID", "")
LINE_LOGIN_CHANNEL_SECRET = os.getenv("LINE_LOGIN_CHANNEL_SECRET", "")
LINE_BOT_BASIC_ID = os.getenv("LINE_BOT_BASIC_ID", "")  # @PDBBot
LINE_BOT_BASE_URL = os.getenv("LINE_BOT_BASE_URL", APP_BASE_URL)


def is_line_configured() -> bool:
    """True ถ้า LINE Messaging API พร้อมใช้งาน (Channel Secret + Access Token).
    LINE Login channel = optional (ถ้าไม่ตั้ง = bot ส่ง notify ได้แต่ link account ไม่ได้).
    """
    return bool(LINE_CHANNEL_SECRET and LINE_CHANNEL_ACCESS_TOKEN)


def is_line_login_configured() -> bool:
    """True ถ้า LINE Login OAuth พร้อม (สำหรับ account linking)."""
    return bool(LINE_LOGIN_CHANNEL_ID and LINE_LOGIN_CHANNEL_SECRET)
