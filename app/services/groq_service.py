from groq import Groq
from typing import List, Optional
import traceback
from app.config import settings
from app.services.resume_parser import get_resume_context

client = None


def get_groq_client():
    global client
    if client is None:
        print(f"🔧 Initializing Groq client with model: {settings.GROQ_MODEL}")
        print(f"🔧 API key prefix: {settings.GROQ_API_KEY[:8]}...")
        client = Groq(api_key=settings.GROQ_API_KEY)
    return client


SYSTEM_PROMPT_TEMPLATE = """You are a professional and friendly AI assistant that represents the person whose resume is provided below. You speak on BEHALF of this person — as if you are their personal career spokesperson.

RESUME CONTENT:
{resume_context}

YOUR PERSONALITY & STYLE:
- Speak in a warm, confident, professional tone
- Refer to the resume owner by their name (extract it from the resume header)
- When introducing the person, give a compelling summary — don't just list raw text
- Use **markdown formatting** to make responses readable: bold key terms, use bullet points for lists, and headers for sections
- Be concise — aim for 3-6 sentences for simple questions, or structured bullets for detail questions
- Add a touch of enthusiasm when highlighting achievements and strengths

HOW TO RESPOND TO COMMON QUESTIONS:

**"Whose resume is this?" / "Who is this?" / "Tell me about yourself"**
→ Give a compelling 3-4 sentence professional intro: Name, current/last role, years of experience, key strengths. End with what makes them stand out.

**"What are their skills?" / "What can they do?"**
→ Group skills by category (e.g., Technical, Soft Skills, Tools) using bullet points. Highlight the strongest ones.

**"What experience do they have?"**
→ Summarize each role with the company name, dates, and 1-2 key achievements — don't dump the entire description.

**"What education do they have?"**
→ List degrees/certifications concisely with institution and year.

RULES:
1. ONLY answer questions related to the resume owner's professional background, skills, experience, education, projects, or career.
2. If a question is NOT related to the resume, politely decline: "I'm here to tell you about [Name]'s professional background! Feel free to ask about their skills, experience, or education. 😊"
3. NEVER fabricate information. If the resume doesn't cover something, say so honestly and suggest what you CAN talk about.
4. NEVER dump raw resume text. Always synthesize, summarize, and present information in a polished way.
5. Keep responses focused and scannable — use formatting to help readers quickly find what they need.
"""

IRRELEVANT_KEYWORDS = [
    "weather", "joke", "recipe", "movie", "game", "sports", "politics",
    "religion", "dating", "gossip", "celebrity", "stock", "crypto",
    "write code", "debug", "fix this", "help me with", "translate",
    "what is the meaning of life", "tell me a story",
]


def is_likely_irrelevant(message: str) -> bool:
    """Quick keyword-based check for obviously irrelevant questions."""
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in IRRELEVANT_KEYWORDS)


async def get_chat_response(
    user_message: str,
    resume_text: str,
    resume_sections: Optional[dict],
    conversation_history: List[dict],
) -> dict:
    """
    Generate a response using Groq LLM with resume context.
    Returns dict with 'reply' and 'is_relevant' fields.
    """
    try:
        groq_client = get_groq_client()
    except Exception as e:
        print(f"❌ Failed to initialize Groq client: {e}")
        traceback.print_exc()
        return {
            "reply": f"Configuration error: Could not initialize AI service. Please check the API key. Error: {str(e)}",
            "is_relevant": True,
        }

    # Build context
    resume_context = get_resume_context(resume_text, resume_sections)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(resume_context=resume_context)

    # Quick irrelevance check
    quick_irrelevant = is_likely_irrelevant(user_message)

    # Build messages array
    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history (last 10 messages for context window management)
    for msg in conversation_history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    # If quick check flagged irrelevant, add a hint to the system
    if quick_irrelevant:
        messages.append({
            "role": "system",
            "content": "Note: This question appears to be off-topic. Please provide a polite fallback response redirecting to professional topics."
        })

    try:
        print(f"📤 Sending request to Groq ({settings.GROQ_MODEL})...")
        response = groq_client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
            top_p=0.9,
        )

        reply = response.choices[0].message.content
        print(f"✅ Got response from Groq ({len(reply)} chars)")

        # Determine relevance from the response
        is_relevant = not quick_irrelevant

        return {
            "reply": reply,
            "is_relevant": is_relevant,
        }

    except Exception as e:
        print(f"❌ Groq API error: {type(e).__name__}: {e}")
        traceback.print_exc()
        return {
            "reply": f"AI service error: {type(e).__name__} — {str(e)}. Please check the backend logs.",
            "is_relevant": True,
        }
