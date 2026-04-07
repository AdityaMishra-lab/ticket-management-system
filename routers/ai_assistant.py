from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from openai import OpenAI
import httpx
import os
import json
import logging
from dotenv import load_dotenv

from database import get_db
from models import Ticket, User
from schemas import AIQuery, AIResponse
from auth import get_current_user

load_dotenv()
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI Assistant"])

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), http_client=httpx.Client())


def fetch_ticket_context(db: Session, current_user: User) -> str:
    """Fetch all tickets visible to this user and format as context for the LLM."""
    from models import UserRole
    if current_user.role == UserRole.admin:
        tickets = db.query(Ticket).all()
    else:
        tickets = db.query(Ticket).filter(Ticket.created_by_id == current_user.id).all()

    if not tickets:
        return "No tickets found."

    ticket_list = []
    for t in tickets:
        ticket_list.append({
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "status": t.status.value,
            "priority": t.priority.value,
            "category": t.category.value,
            "created_by_id": t.created_by_id,
            "assigned_to_id": t.assigned_to_id,
            "created_at": str(t.created_at),
            "updated_at": str(t.updated_at),
        })

    return json.dumps(ticket_list, indent=2)


@router.post("/ask", response_model=AIResponse)
def ask_ai(
    payload: AIQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ask natural language questions about your tickets.
    Examples:
    - "What is the status of ticket 5?"
    - "Show all high priority open tickets"
    - "Summarize ticket 3"
    - "How many tickets are unresolved?"
    """
    logger.info(f"AI query from user {current_user.id}: '{payload.query}'")

    ticket_context = fetch_ticket_context(db, current_user)

    system_prompt = """You are a helpful ticket management assistant.
You will be given a JSON list of support tickets and a user's natural language question.
Answer the question accurately and concisely based ONLY on the ticket data provided.
If the answer is not in the data, say so clearly.
Do not make up ticket IDs, statuses, or any data not present in the context.
Format your answer in plain text, using bullet points when listing multiple tickets."""

    user_message = f"""Here are the tickets:

{ticket_context}

User question: {payload.query}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=500,
            temperature=0.2,
        )
        answer = response.choices[0].message.content.strip()
        logger.info(f"AI responded to user {current_user.id} query successfully")
        return AIResponse(query=payload.query, answer=answer)

    except Exception as e:
        logger.error(f"OpenAI API error for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")
