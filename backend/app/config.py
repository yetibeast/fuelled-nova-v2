import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DATABASE_URL = os.environ["DATABASE_URL"]
STATE_DATABASE_URL = os.environ.get("STATE_DATABASE_URL", "")
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
PRICING_V2_ENABLED = os.environ.get("PRICING_V2_ENABLED", "false").lower() == "true"
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
# Langfuse observability (optional — graceful no-op when keys are empty)
LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")

_jwt_secret = os.environ.get("JWT_SECRET", "")
if not _jwt_secret:
    raise RuntimeError("JWT_SECRET environment variable is required. Set it in .env or your deployment config.")
JWT_SECRET = _jwt_secret

# JSONL logs — API spend, feedback, batch/reports history.
# Prod (Railway) must point this at a mounted volume path (e.g. /data/logs)
# so history survives container redeploys. Local default is backend/logs/.
LOG_DIR = os.environ.get(
    "LOG_DIR",
    os.path.join(os.path.dirname(__file__), "..", "logs"),
)
