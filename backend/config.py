"""
Central configuration for the RxResolveAI backend.

Every setting can be overridden with an environment variable, which is how the
tests point the app at a temporary database.
"""
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

# --- Storage -----------------------------------------------------------------
DATABASE_PATH = os.getenv("RXR_DATABASE_PATH", str(BACKEND_DIR / "rxresolve.db"))
POLICY_DIR = Path(os.getenv("RXR_POLICY_DIR", str(PROJECT_ROOT / "sample_policies")))
SAMPLE_DATA_DIR = Path(os.getenv("RXR_SAMPLE_DATA_DIR", str(PROJECT_ROOT / "sample_data")))

# Load demo users and demo cases on first start (when the tables are empty).
SEED_DEMO_DATA = os.getenv("RXR_SEED_DEMO_DATA", "1") == "1"

# --- Local AI (Ollama) -------------------------------------------------------
# Set RXR_USE_OLLAMA=0 to force the rule-based fallback.
USE_OLLAMA = os.getenv("RXR_USE_OLLAMA", "1") == "1"
# 127.0.0.1 instead of "localhost": on Windows "localhost" tries IPv6 first, which makes
# the "is Ollama running?" check slow when it is not installed.
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT", "90"))

# --- Uploads -----------------------------------------------------------------
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".txt", ".docx"}

# --- Auth --------------------------------------------------------------------
SESSION_HOURS = 12
