from datetime import datetime, timezone, timedelta

import bcrypt
import jwt
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.config import JWT_SECRET
from app.db.session import get_session

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
async def login(body: LoginRequest):
    async with get_session() as session:
        row = (
            await session.execute(
                text(
                    "SELECT id, email, name, role, password_hash "
                    "FROM users WHERE email = :email AND status = 'active'"
                ),
                {"email": body.email.strip().lower()},
            )
        ).fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not bcrypt.checkpw(body.password.encode(), row.password_hash.encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = jwt.encode(
        {
            "sub": str(row.id),
            "email": row.email,
            "role": row.role,
            "name": row.name,
            "exp": datetime.now(timezone.utc) + timedelta(hours=24),
        },
        JWT_SECRET,
        algorithm="HS256",
    )

    # Update last login (fire-and-forget)
    async with get_session() as session:
        await session.execute(
            text("UPDATE users SET last_login_at = NOW() WHERE id = :id"),
            {"id": row.id},
        )
        await session.commit()

    return {
        "token": token,
        "user": {
            "id": str(row.id),
            "name": row.name,
            "email": row.email,
            "role": row.role,
        },
    }


@router.get("/me")
async def me(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    try:
        payload = jwt.decode(
            authorization[7:], JWT_SECRET, algorithms=["HS256"]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    return {
        "id": payload["sub"],
        "name": payload.get("name", ""),
        "email": payload.get("email", ""),
        "role": payload.get("role", ""),
    }
