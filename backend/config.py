"""Configuration for Project KEY backend."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenRouter API
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
LLM_MODEL = "google/gemini-2.5-flash"

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

