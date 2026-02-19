from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ─── Auth Models ───────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin: dict


class AdminProfile(BaseModel):
    email: str
    created_at: datetime


# ─── Resume Models ─────────────────────────────────────────

class ResumeOut(BaseModel):
    id: str
    filename: str
    uploaded_at: datetime
    is_active: bool
    sections: Optional[dict] = None


class ResumeListResponse(BaseModel):
    resumes: List[ResumeOut]
    total: int


# ─── Chat Models ───────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    is_relevant: bool = True


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatSessionOut(BaseModel):
    session_id: str
    messages_count: int
    last_message: Optional[str] = None
    created_at: datetime
    visitor_ip: Optional[str] = None


# ─── Analytics Models ──────────────────────────────────────

class AnalyticsStats(BaseModel):
    total_sessions: int
    total_messages: int
    today_sessions: int
    today_messages: int
    popular_questions: List[dict]
    daily_activity: List[dict]
