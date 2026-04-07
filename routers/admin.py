from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
import logging

from database import get_db
from models import User, Ticket, TicketStatus, TicketPriority, TicketCategory, UserRole
from schemas import TicketOut, TicketUpdate, TicketStatusUpdate, AdminStats, UserOut
from auth import get_current_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/tickets", response_model=List[TicketOut])
def admin_list_tickets(
    status: Optional[TicketStatus] = Query(None),
    priority: Optional[TicketPriority] = Query(None),
    category: Optional[TicketCategory] = Query(None),
    created_by_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("created_at", description="created_at | priority | status"),
    order: Optional[str] = Query("desc", description="asc | desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    query = db.query(Ticket)

    if status:
        query = query.filter(Ticket.status == status)
    if priority:
        query = query.filter(Ticket.priority == priority)
    if category:
        query = query.filter(Ticket.category == category)
    if created_by_id:
        query = query.filter(Ticket.created_by_id == created_by_id)
    if search:
        query = query.filter(
            Ticket.title.ilike(f"%{search}%") | Ticket.description.ilike(f"%{search}%")
        )

    sort_col = getattr(Ticket, sort_by, Ticket.created_at)
    if order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    offset = (page - 1) * page_size
    tickets = query.offset(offset).limit(page_size).all()

    logger.info(f"Admin {current_admin.id} listed tickets: page={page}, count={len(tickets)}")
    return tickets


@router.get("/stats", response_model=AdminStats)
def admin_stats(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    total = db.query(Ticket).count()
    open_t = db.query(Ticket).filter(Ticket.status == TicketStatus.open).count()
    in_prog = db.query(Ticket).filter(Ticket.status == TicketStatus.in_progress).count()
    resolved = db.query(Ticket).filter(Ticket.status == TicketStatus.resolved).count()
    closed = db.query(Ticket).filter(Ticket.status == TicketStatus.closed).count()
    users = db.query(User).count()
    high_open = db.query(Ticket).filter(
        Ticket.priority == TicketPriority.high,
        Ticket.status == TicketStatus.open
    ).count()
    critical_open = db.query(Ticket).filter(
        Ticket.priority == TicketPriority.critical,
        Ticket.status == TicketStatus.open
    ).count()

    logger.info(f"Admin {current_admin.id} fetched stats")
    return AdminStats(
        total_tickets=total,
        open_tickets=open_t,
        in_progress_tickets=in_prog,
        resolved_tickets=resolved,
        closed_tickets=closed,
        total_users=users,
        high_priority_open=high_open,
        critical_priority_open=critical_open
    )


@router.get("/tickets/{ticket_id}", response_model=TicketOut)
def admin_get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.put("/tickets/{ticket_id}", response_model=TicketOut)
def admin_update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(ticket, key, value)

    db.commit()
    db.refresh(ticket)
    logger.info(f"Admin {current_admin.id} updated ticket {ticket_id}")
    return ticket


@router.patch("/tickets/{ticket_id}/status", response_model=TicketOut)
def admin_update_ticket_status(
    ticket_id: int,
    payload: TicketStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket.status = payload.status
    db.commit()
    db.refresh(ticket)
    logger.info(f"Admin {current_admin.id} changed ticket {ticket_id} status to {payload.status}")
    return ticket


@router.delete("/tickets/{ticket_id}", status_code=204)
def admin_delete_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    db.delete(ticket)
    db.commit()
    logger.info(f"Admin {current_admin.id} deleted ticket {ticket_id}")


@router.get("/users", response_model=List[UserOut])
def admin_list_users(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    return db.query(User).all()
