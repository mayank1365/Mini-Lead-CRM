from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import LeadStatus
from app.schemas import LeadCreate, LeadResponse, LeadStatusUpdate, LeadUpdate
from app.crud import (
    InvalidStatusTransition,
    create_lead,
    delete_lead,
    get_lead,
    get_leads,
    transition_lead_status,
    update_lead,
)

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_new_lead(lead_in: LeadCreate, db: Session = Depends(get_db)):
    """Create a new lead.

    Every lead starts with status NEW.
    """
    return create_lead(db, lead_in)


@router.get("", response_model=List[LeadResponse])
def read_leads(status: Optional[LeadStatus] = None, db: Session = Depends(get_db)):
    """Get all leads, optionally filtered by status."""
    return get_leads(db, status=status)


@router.get("/{lead_id}", response_model=LeadResponse)
def read_lead_by_id(lead_id: str, db: Session = Depends(get_db)):
    """Get lead by ID."""
    db_lead = get_lead(db, lead_id)
    if not db_lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead with ID {lead_id} not found",
        )
    return db_lead


@router.put("/{lead_id}", response_model=LeadResponse)
def update_lead_details(lead_id: str, lead_in: LeadUpdate, db: Session = Depends(get_db)):
    """Update lead details (name, email, phone, source).

    Status updates are ignored/not allowed here to enforce transition rules.
    """
    db_lead = get_lead(db, lead_id)
    if not db_lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead with ID {lead_id} not found",
        )
    return update_lead(db, db_lead, lead_in)


@router.delete("/{lead_id}")
def delete_lead_by_id(lead_id: str, db: Session = Depends(get_db)):
    """Delete a lead by ID."""
    db_lead = get_lead(db, lead_id)
    if not db_lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead with ID {lead_id} not found",
        )
    delete_lead(db, db_lead)
    return {"message": f"Lead with ID {lead_id} deleted successfully"}


@router.patch("/{lead_id}/status", response_model=LeadResponse)
def patch_lead_status(lead_id: str, status_update: LeadStatusUpdate, db: Session = Depends(get_db)):
    """Transition a lead between statuses following the state machine rules."""
    db_lead = get_lead(db, lead_id)
    if not db_lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead with ID {lead_id} not found",
        )
    
    try:
        updated_lead = transition_lead_status(db, db_lead, status_update.status)
        return updated_lead
    except InvalidStatusTransition as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": str(e)},
        )
