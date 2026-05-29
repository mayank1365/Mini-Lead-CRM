from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models import LeadStatus


class LeadBase(BaseModel):
    name: str = Field(..., min_length=1, description="The full name of the lead")
    email: EmailStr = Field(..., description="The contact email address of the lead")
    phone: Optional[str] = Field(None, description="Optional phone number of the lead")
    source: Optional[str] = Field(None, description="Optional source of the lead (e.g. website, referral)")


class LeadCreate(LeadBase):
    pass


class LeadUpdate(LeadBase):
    # PUT requires full replacement of required fields
    pass


class LeadStatusUpdate(BaseModel):
    status: LeadStatus = Field(..., description="The new status to transition to")


class LeadResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    phone: Optional[str] = None
    status: LeadStatus
    source: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeadBulkUpdateItem(BaseModel):
    id: str = Field(..., description="The ID of the lead to update")
    name: Optional[str] = Field(None, min_length=1, description="The full name of the lead")
    email: Optional[EmailStr] = Field(None, description="The contact email address of the lead")
    phone: Optional[str] = Field(None, description="Optional phone number of the lead")
    source: Optional[str] = Field(None, description="Optional source of the lead")


class BulkResultItem(BaseModel):
    index: int
    success: bool
    lead: Optional[LeadResponse] = None
    error: Optional[str] = None


class BulkResponse(BaseModel):
    total: int
    successful: int
    failed: int
    results: List[BulkResultItem]
