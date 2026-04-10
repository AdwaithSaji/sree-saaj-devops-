from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, ForeignKey, Enum, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import enum
from database import Base


class EventType(str, enum.Enum):
    wedding = "wedding"
    birthday = "birthday"
    corporate = "corporate"
    funeral = "funeral"
    stage = "stage"
    outdoor_catering = "outdoor_catering"
    custom = "custom"


class EventStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class BookingStatus(str, enum.Enum):
    new = "new"
    contacted = "contacted"
    converted = "converted"
    rejected = "rejected"


class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    event_type = Column(Enum(EventType), nullable=False)
    client_name = Column(String(255), nullable=False)
    client_phone = Column(String(20), nullable=False)
    client_email = Column(String(255), nullable=True)
    event_date = Column(DateTime(timezone=True), nullable=False)
    venue = Column(String(500), nullable=False)
    guest_count = Column(Integer, nullable=False, default=0)
    status = Column(Enum(EventStatus), nullable=False, default=EventStatus.pending)
    catering_required = Column(Boolean, default=False)
    decoration_required = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class EventStaff(Base):
    __tablename__ = "event_staff"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    staff_id = Column(UUID(as_uuid=True), nullable=False)
    role = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BookingInquiry(Base):
    __tablename__ = "booking_inquiries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(255), nullable=True)
    event_type = Column(Enum(EventType), nullable=False)
    event_date = Column(DateTime(timezone=True), nullable=True)
    venue = Column(String(500), nullable=True)
    guest_count = Column(Integer, nullable=True)
    catering_required = Column(Boolean, default=False)
    decoration_required = Column(Boolean, default=False)
    special_requirements = Column(Text, nullable=True)
    status = Column(Enum(BookingStatus), nullable=False, default=BookingStatus.new)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
