"""Seed initial admin credentials into MongoDB."""
import asyncio
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.auth.utils import hash_password


async def seed_admin():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DB_NAME]

    existing = await db.admins.find_one({"email": settings.ADMIN_EMAIL})
    if existing:
        print(f"✅ Admin '{settings.ADMIN_EMAIL}' already exists, skipping seed.")
        client.close()
        return

    admin_doc = {
        "email": settings.ADMIN_EMAIL,
        "password": hash_password(settings.ADMIN_PASSWORD),
        "created_at": datetime.utcnow(),
    }
    await db.admins.insert_one(admin_doc)
    print(f"✅ Admin seeded: {settings.ADMIN_EMAIL}")
    client.close()


if __name__ == "__main__":
    asyncio.run(seed_admin())
