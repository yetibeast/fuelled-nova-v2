import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DATABASE_URL = os.environ["DATABASE_URL"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
PRICING_V2_ENABLED = os.environ.get("PRICING_V2_ENABLED", "false").lower() == "true"
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
_jwt_secret = os.environ.get("JWT_SECRET", "")
if not _jwt_secret:
    raise RuntimeError("JWT_SECRET environment variable is required. Set it in .env or your deployment config.")
JWT_SECRET = _jwt_secret
