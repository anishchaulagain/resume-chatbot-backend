from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

client: AsyncIOMotorClient = None
db = None


async def connect_db():
    global client, db
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DB_NAME]
    # Create indexes
    await db.admins.create_index("email", unique=True)
    await db.resumes.create_index("is_active")
    await db.chat_sessions.create_index("session_id", unique=True)
    await db.chat_sessions.create_index("created_at")
    await db.analytics.create_index("created_at")
    print(f"✅ Connected to MongoDB: {settings.DB_NAME}")


async def close_db():
    global client
    if client:
        client.close()
        print("🔌 MongoDB connection closed")


def get_db():
    return db
