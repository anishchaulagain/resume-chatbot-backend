from fastapi import APIRouter, Depends
from datetime import datetime, timedelta

from app.database import get_db
from app.auth.dependencies import get_current_admin
from app.models.schemas import AnalyticsStats, ChatSessionOut

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/stats", response_model=AnalyticsStats)
async def get_stats(admin=Depends(get_current_admin)):
    db = get_db()

    # Total counts
    total_sessions = await db.chat_sessions.count_documents({})
    total_messages = await db.analytics.count_documents({"event_type": "chat_message"})

    # Today's counts
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_sessions = await db.chat_sessions.count_documents(
        {"created_at": {"$gte": today_start}}
    )
    today_messages = await db.analytics.count_documents(
        {"event_type": "chat_message", "created_at": {"$gte": today_start}}
    )

    # Popular questions (top 10)
    pipeline = [
        {"$match": {"event_type": "chat_message", "is_relevant": True}},
        {"$group": {"_id": "$question", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    popular_questions = []
    async for doc in db.analytics.aggregate(pipeline):
        popular_questions.append({"question": doc["_id"], "count": doc["count"]})

    # Daily activity (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    daily_pipeline = [
        {"$match": {"event_type": "chat_message", "created_at": {"$gte": seven_days_ago}}},
        {
            "$group": {
                "_id": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                },
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    daily_activity = []
    async for doc in db.analytics.aggregate(daily_pipeline):
        daily_activity.append({"date": doc["_id"], "count": doc["count"]})

    return AnalyticsStats(
        total_sessions=total_sessions,
        total_messages=total_messages,
        today_sessions=today_sessions,
        today_messages=today_messages,
        popular_questions=popular_questions,
        daily_activity=daily_activity,
    )


@router.get("/sessions")
async def get_sessions(
    page: int = 1,
    limit: int = 20,
    admin=Depends(get_current_admin),
):
    db = get_db()
    skip = (page - 1) * limit

    sessions = []
    async for s in (
        db.chat_sessions.find()
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    ):
        messages = s.get("messages", [])
        last_msg = messages[-1]["content"] if messages else None

        sessions.append(
            ChatSessionOut(
                session_id=s["session_id"],
                messages_count=len(messages),
                last_message=last_msg[:100] if last_msg else None,
                created_at=s["created_at"],
                visitor_ip=s.get("visitor_ip"),
            ).model_dump()
        )

    total = await db.chat_sessions.count_documents({})

    return {
        "sessions": sessions,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
    }
