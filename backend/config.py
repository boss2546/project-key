"""Configuration for Project KEY backend."""
import os
import secrets
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ─── App Version (single source of truth) ───
# Bump this when releasing. All version strings exposed to clients
# (Swagger /docs, /api/mcp/info, MCP serverInfo) read from here.
APP_VERSION = "5.9.3"

# OpenRouter API
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
LLM_MODEL = "google/gemini-3-flash-preview"            # Chat & lightweight tasks (fast, cheap)
LLM_MODEL_PRO = "google/gemini-3.1-pro-preview"         # Data management: organize, summarize, text cleanup (smart)

# Limits
MAX_FILE_SIZE_MB = 10

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

# ─── Admin Password (from env, no longer hardcoded) ───
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "1234")

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
