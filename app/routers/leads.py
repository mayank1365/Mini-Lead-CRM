from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import LeadStatus
from pydantic import ValidationError
from app.schemas import (
    BulkResponse,
    BulkResultItem,
    LeadBulkUpdateItem,
    LeadCreate,
    LeadResponse,
    LeadStatusUpdate,
    LeadUpdate,
)
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


def format_validation_error(exc: ValidationError) -> str:
    errors = exc.errors()
    formatted = []
    for err in errors:
        field = ".".join(str(loc) for loc in err['loc'])
        msg = err['msg']
        err_type = err['type']
        if err_type == "missing":
            formatted.append(f"{field} is required")
        else:
            if field:
                formatted.append(f"{field}: {msg}")
            else:
                formatted.append(msg)
    return "; ".join(formatted)


@router.post("/bulk", response_model=BulkResponse, status_code=status.HTTP_200_OK)
def create_bulk_leads(leads_in: List[dict], db: Session = Depends(get_db)):
    """Create multiple leads at once.

    Accepts an array of lead objects. Returns an outcome summary.
    """
    from sqlalchemy.exc import IntegrityError
    from app.models import Lead

    results = []
    successful = 0
    failed = 0

    for idx, item in enumerate(leads_in):
        try:
            # Validate input item against LeadCreate
            lead_create = LeadCreate.model_validate(item)

            # Check database for email uniqueness to avoid duplicate entries in same transaction block
            existing_lead = db.query(Lead).filter(Lead.email == lead_create.email).first()
            if existing_lead:
                results.append(
                    BulkResultItem(
                        index=idx,
                        success=False,
                        error="Email already exists",
                    )
                )
                failed += 1
                continue

            db_lead = Lead(
                name=lead_create.name,
                email=lead_create.email,
                phone=lead_create.phone,
                source=lead_create.source,
                status=LeadStatus.NEW,
            )
            db.add(db_lead)
            db.commit()
            db.refresh(db_lead)

            results.append(
                BulkResultItem(
                    index=idx,
                    success=True,
                    lead=LeadResponse.model_validate(db_lead),
                )
            )
            successful += 1

        except ValidationError as e:
            error_msg = format_validation_error(e)
            results.append(
                BulkResultItem(
                    index=idx,
                    success=False,
                    error=error_msg,
                )
            )
            failed += 1
        except IntegrityError:
            db.rollback()
            results.append(
                BulkResultItem(
                    index=idx,
                    success=False,
                    error="Email already exists",
                )
            )
            failed += 1
        except Exception as e:
            db.rollback()
            results.append(
                BulkResultItem(
                    index=idx,
                    success=False,
                    error=str(e),
                )
            )
            failed += 1

    return BulkResponse(
        total=len(leads_in),
        successful=successful,
        failed=failed,
        results=results,
    )


@router.put("/bulk", response_model=BulkResponse, status_code=status.HTTP_200_OK)
def update_bulk_leads(updates_in: List[dict], db: Session = Depends(get_db)):
    """Update multiple leads at once.

    Accepts an array of partial updates, each containing an `id` field.
    """
    from sqlalchemy.exc import IntegrityError
    from app.models import Lead

    results = []
    successful = 0
    failed = 0

    for idx, item in enumerate(updates_in):
        try:
            # First, check if ID is present
            if "id" not in item:
                results.append(
                    BulkResultItem(
                        index=idx,
                        success=False,
                        error="id is required",
                    )
                )
                failed += 1
                continue

            # Validate input item against LeadBulkUpdateItem
            update_item = LeadBulkUpdateItem.model_validate(item)

            # Fetch the existing lead by ID
            db_lead = db.query(Lead).filter(Lead.id == update_item.id).first()
            if not db_lead:
                results.append(
                    BulkResultItem(
                        index=idx,
                        success=False,
                        error=f"Lead with ID {update_item.id} not found",
                    )
                )
                failed += 1
                continue

            # If email is being updated, check for uniqueness constraint conflict
            if update_item.email is not None and update_item.email != db_lead.email:
                existing_email_lead = db.query(Lead).filter(Lead.email == update_item.email).first()
                if existing_email_lead:
                    results.append(
                        BulkResultItem(
                            index=idx,
                            success=False,
                            error="Email already exists",
                        )
                    )
                    failed += 1
                    continue

            # Apply partial update (only fields explicitly provided)
            update_data = update_item.model_dump(exclude_unset=True)
            # Remove id since we don't update the primary key ID
            update_data.pop("id", None)

            for field, value in update_data.items():
                setattr(db_lead, field, value)

            try:
                db.commit()
                db.refresh(db_lead)
            except IntegrityError:
                db.rollback()
                results.append(
                    BulkResultItem(
                        index=idx,
                        success=False,
                        error="Email already exists",
                    )
                )
                failed += 1
                continue

            results.append(
                BulkResultItem(
                    index=idx,
                    success=True,
                    lead=LeadResponse.model_validate(db_lead),
                )
            )
            successful += 1

        except ValidationError as e:
            error_msg = format_validation_error(e)
            results.append(
                BulkResultItem(
                    index=idx,
                    success=False,
                    error=error_msg,
                )
            )
            failed += 1
        except Exception as e:
            db.rollback()
            results.append(
                BulkResultItem(
                    index=idx,
                    success=False,
                    error=str(e),
                )
            )
            failed += 1

    return BulkResponse(
        total=len(updates_in),
        successful=successful,
        failed=failed,
        results=results,
    )


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
