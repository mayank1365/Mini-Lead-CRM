from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import Lead, LeadStatus
from app.schemas import LeadCreate, LeadUpdate


class InvalidStatusTransition(ValueError):
    """Exception raised when a lead status transition is invalid."""
    pass


# Lead status transition state machine
VALID_TRANSITIONS = {
    LeadStatus.NEW: {LeadStatus.CONTACTED, LeadStatus.LOST},
    LeadStatus.CONTACTED: {LeadStatus.QUALIFIED, LeadStatus.LOST},
    LeadStatus.QUALIFIED: {LeadStatus.CONVERTED, LeadStatus.LOST},
    LeadStatus.CONVERTED: set(),  # Terminal state
    LeadStatus.LOST: set(),       # Terminal state


def get_lead(db: Session, lead_id: str) -> Optional[Lead]:
    return db.query(Lead).filter(Lead.id == lead_id).first()


def get_leads(db: Session, status: Optional[LeadStatus] = None) -> List[Lead]:
    query = db.query(Lead)
    if status is not None:
        query = query.filter(Lead.status == status)
    return query.all()


def create_lead(db: Session, lead_in: LeadCreate) -> Lead:
    db_lead = Lead(
        name=lead_in.name,
        email=lead_in.email,
        phone=lead_in.phone,
        source=lead_in.source,
        status=LeadStatus.NEW,  # Every lead starts with status NEW
    )
    db.add(db_lead)
    db.commit()
    db.refresh(db_lead)
    return db_lead


def update_lead(db: Session, db_lead: Lead, lead_in: LeadUpdate) -> Lead:
    # Update all fields except ID, status, created_at, updated_at
    # Use setattr to avoid static typechecker complaints about SQLAlchemy Column descriptors
    setattr(db_lead, "name", lead_in.name)
    setattr(db_lead, "email", lead_in.email)
    setattr(db_lead, "phone", lead_in.phone)
    setattr(db_lead, "source", lead_in.source)
    
    db.commit()
    db.refresh(db_lead)
    return db_lead


def transition_lead_status(db: Session, db_lead: Lead, next_status: LeadStatus) -> Lead:
    current_status = db_lead.status
    
    # If the requested status is already the current status, treat it as a no-op (return the lead)
    # or raise an error. Standard REST state machine usually allows no-op, but let's check
    # if it's considered an invalid transition in this sales pipeline. To be strict and precise,
    # let's validate against VALID_TRANSITIONS. If current == next, it's not in the set of allowed transitions.
    if next_status == current_status:
        # A no-op is often fine, but if they explicitly request a state transition,
        # let's make it a no-op to be robust, OR we can raise an error if they want to be strict.
        # Actually, let's keep it simple: if current_status == next_status, it's a no-op.
        return db_lead

    allowed_next = VALID_TRANSITIONS.get(current_status, set())  # type: ignore[arg-type]
    if next_status not in allowed_next:
        raise InvalidStatusTransition(
            f"Invalid status transition from {current_status.value} to {next_status.value}"
        )
    
    setattr(db_lead, "status", next_status)
    db.commit()
    db.refresh(db_lead)
    return db_lead


def delete_lead(db: Session, db_lead: Lead) -> None:
    db.delete(db_lead)
    db.commit()
