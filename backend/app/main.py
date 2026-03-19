import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import text
from app.config import CORS_ORIGINS
from app.api import price
from app.db.session import get_session

_FRONTEND_HTML = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "chat-interface", "index.html")

app = FastAPI(title="Fuelled Nova v2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(price.router, prefix="/api")


@app.get("/api/health")
async def health():
    async with get_session() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM listings"))
        count = result.scalar()
    return {"status": "ok", "listings_count": count}


@app.get("/")
async def root():
    return FileResponse(_FRONTEND_HTML)
