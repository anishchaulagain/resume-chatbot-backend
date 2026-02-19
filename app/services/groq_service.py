from groq import Groq
from typing import List, Optional
from app.config import settings
from app.services.resume_parser import get_resume_context

client = None


def get_groq_client():
    global client
    if client is None:
        client = Groq(api_key=settings.GROQ_API_KEY)
    return client


SYSTEM_PROMPT_TEMPLATE = """You are a professional AI assistant that represents the resume owner. Your job is to answer questions about the person whose resume is provided below. You should respond in a friendly, professional, and helpful manner as if you are representing this person.

RESUME CONTENT:
{resume_context}

RULES:
1. Only answer questions that are directly related to the resume owner's professional background, skills, experience, education, projects, or career.
2. If a question is NOT related to the resume or the person described in it, politely decline and redirect the conversation back to professional topics.
3. For irrelevant questions (e.g., personal opinions, unrelated trivia, coding help), respond with a polite fallback message.
4. Be concise but informative. Use bullet points when listing multiple items.
5. If the resume doesn't contain information to answer a specific professional question, say so honestly rather than making things up.
6. Always maintain a professional and positive tone about the resume owner.
7. You can make reasonable inferences from the resume content but never fabricate information.
8. When describing skills or experience, emphasize strengths and achievements.

FALLBACK RESPONSE GUIDELINES:
- For completely off-topic questions: "I appreciate your curiosity! However, I'm specifically designed to discuss [Name]'s professional background and qualifications. Feel free to ask about their skills, experience, projects, or education!"
- For questions about information not in the resume: "That's a great question, but I don't have that specific information in the resume. You might want to reach out directly for more details. In the meantime, I can tell you about [suggest related topic from resume]."
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
    groq_client = get_groq_client()

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
        response = groq_client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
            top_p=0.9,
        )

        reply = response.choices[0].message.content

        # Determine relevance from the response
        is_relevant = not quick_irrelevant

        return {
            "reply": reply,
            "is_relevant": is_relevant,
        }

    except Exception as e:
        print(f"Groq API error: {e}")
        return {
            "reply": "I'm sorry, I'm experiencing some technical difficulties right now. Please try again in a moment.",
            "is_relevant": True,
        }
