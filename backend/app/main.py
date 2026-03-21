import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from app.config import CORS_ORIGINS
from app.api import price, admin
from app.db.session import get_session

_FRONTEND_HTML = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "chat-interface", "index.html")
_APP_HTML = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "app", "index.html")
_LOGIN_HTML = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "app", "login.html")
_IMAGES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "app", "images")

app = FastAPI(title="Fuelled Nova v2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(price.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/api/health")
async def health():
    async with get_session() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM listings"))
        count = result.scalar()
    return {"status": "ok", "listings_count": count}


@app.get("/login")
async def login():
    return FileResponse(_LOGIN_HTML)


@app.get("/app")
async def app_shell():
    return FileResponse(_APP_HTML)


@app.get("/chat")
async def chat():
    return FileResponse(_FRONTEND_HTML)


@app.get("/")
async def root():
    return FileResponse(_FRONTEND_HTML)


if os.path.isdir(_IMAGES_DIR):
    app.mount("/images", StaticFiles(directory=_IMAGES_DIR), name="images")
