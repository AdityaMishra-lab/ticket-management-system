from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
from models import UserRole, TicketStatus, TicketPriority, TicketCategory


# ─── Auth Schemas ───────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: Optional[UserRole] = UserRole.user

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v

    @field_validator("username")
    @classmethod
    def username_valid(cls, v):
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        return v.strip()


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ─── Ticket Schemas ──────────────────────────────────────────────────────────────

class TicketCreate(BaseModel):
    title: str
    description: str
    priority: Optional[TicketPriority] = TicketPriority.medium
    category: Optional[TicketCategory] = TicketCategory.other
    assigned_to_id: Optional[int] = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Description cannot be empty")
        return v.strip()


class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[TicketPriority] = None
    category: Optional[TicketCategory] = None
    assigned_to_id: Optional[int] = None


class TicketStatusUpdate(BaseModel):
    status: TicketStatus


class TicketOut(BaseModel):
    id: int
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    category: TicketCategory
    created_by_id: int
    assigned_to_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    creator: Optional[UserOut] = None
    assignee: Optional[UserOut] = None

    model_config = {"from_attributes": True}


# ─── Admin Schemas ───────────────────────────────────────────────────────────────

class AdminStats(BaseModel):
    total_tickets: int
    open_tickets: int
    in_progress_tickets: int
    resolved_tickets: int
    closed_tickets: int
    total_users: int
    high_priority_open: int
    critical_priority_open: int


# ─── AI Assistant Schema ─────────────────────────────────────────────────────────

class AIQuery(BaseModel):
    query: str

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()


class AIResponse(BaseModel):
    query: str
    answer: str
