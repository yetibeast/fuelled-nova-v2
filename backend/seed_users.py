"""Seed users with bcrypt password hashes.

Uses existing users table schema (id, email, password_hash, name, role, status).

Usage:
    cd backend && PYTHONPATH=. python3 seed_users.py
"""

import asyncio

import bcrypt
from sqlalchemy import text

from app.db.session import get_session

USERS = [
    ("curtis@arcanosai.com", "Curtis Lynn", "admin"),
    ("harsh@arcanosai.com", "Harsh Kansara", "analyst"),
    ("mark@fuelledmarketing.com", "Mark Le Dain", "admin"),
    ("raj@fuelledmarketing.com", "Raj Singh", "analyst"),
]

PASSWORD = "fuelled2026"


async def main():
    pw_hash = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode()

    async with get_session() as session:
        # Ensure password_hash column exists (may already from prior migration)
        await session.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)"
        ))
        for email, name, role in USERS:
            await session.execute(
                text(
                    "INSERT INTO users (id, email, password_hash, name, role) "
                    "VALUES (gen_random_uuid(), :email, :pw, :name, :role) "
                    "ON CONFLICT (email) DO UPDATE SET password_hash = :pw"
                ),
                {"email": email, "pw": pw_hash, "name": name, "role": role},
            )
        await session.commit()

    print(f"Seeded {len(USERS)} users (password: {PASSWORD})")


if __name__ == "__main__":
    asyncio.run(main())
