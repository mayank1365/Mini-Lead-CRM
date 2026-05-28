import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Enum, String
from app.database import Base


class LeadStatus(str, enum.Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    QUALIFIED = "QUALIFIED"
    CONVERTED = "CONVERTED"
    LOST = "LOST"


def generate_short_uuid() -> str:
    """Generate an 8-character unique hex string resembling the first block of a UUID."""
    return uuid.uuid4().hex[:8]


class Lead(Base):
    __tablename__ = "leads"

    id = Column(String(36), primary_key=True, default=generate_short_uuid, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True, index=True)
    phone = Column(String, nullable=True)
    status = Column(Enum(LeadStatus), nullable=False, default=LeadStatus.NEW)
    source = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
