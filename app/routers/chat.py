from fastapi import APIRouter, HTTPException, Request
from datetime import datetime
import uuid

from app.database import get_db
from app.models.schemas import ChatRequest, ChatResponse
from app.services.groq_service import get_chat_response

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request):
    db = get_db()

    # Get active resume
    resume = await db.resumes.find_one({"is_active": True})
    if not resume:
        raise HTTPException(
            status_code=404,
            detail="No resume has been uploaded yet. Please ask the admin to upload a resume.",
        )

    # Get or create session
    session_id = body.session_id or str(uuid.uuid4())

    session = await db.chat_sessions.find_one({"session_id": session_id})
    if not session:
        session = {
            "session_id": session_id,
            "messages": [],
            "created_at": datetime.utcnow(),
            "visitor_ip": request.client.host if request.client else None,
        }
        await db.chat_sessions.insert_one(session)

    conversation_history = session.get("messages", [])

    # Get AI response
    result = await get_chat_response(
        user_message=body.message,
        resume_text=resume["raw_text"],
        resume_sections=resume.get("sections"),
        conversation_history=conversation_history,
    )

    # Save messages to session
    now = datetime.utcnow()
    user_msg = {"role": "user", "content": body.message, "timestamp": now.isoformat()}
    assistant_msg = {
        "role": "assistant",
        "content": result["reply"],
        "timestamp": now.isoformat(),
    }

    await db.chat_sessions.update_one(
        {"session_id": session_id},
        {
            "$push": {"messages": {"$each": [user_msg, assistant_msg]}},
            "$set": {"updated_at": now},
        },
    )

    # Log analytics event
    await db.analytics.insert_one(
        {
            "event_type": "chat_message",
            "session_id": session_id,
            "question": body.message,
            "is_relevant": result["is_relevant"],
            "created_at": now,
        }
    )

    return ChatResponse(
        reply=result["reply"],
        session_id=session_id,
        is_relevant=result["is_relevant"],
    )


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    db = get_db()
    session = await db.chat_sessions.find_one({"session_id": session_id})
    if not session:
        return {"messages": [], "session_id": session_id}

    return {
        "session_id": session_id,
        "messages": session.get("messages", []),
        "created_at": session.get("created_at"),
    }
