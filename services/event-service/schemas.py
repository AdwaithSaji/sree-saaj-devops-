from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID
from models import EventType, EventStatus, BookingStatus


class EventCreate(BaseModel):
    name: str
    event_type: EventType
    client_name: str
    client_phone: str
    client_email: Optional[str] = None
    event_date: datetime
    venue: str
    guest_count: int = 0
    catering_required: bool = False
    decoration_required: bool = False
    notes: Optional[str] = None


class EventUpdate(BaseModel):
    name: Optional[str] = None
    event_type: Optional[EventType] = None
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    client_email: Optional[str] = None
    event_date: Optional[datetime] = None
    venue: Optional[str] = None
    guest_count: Optional[int] = None
    status: Optional[EventStatus] = None
    catering_required: Optional[bool] = None
    decoration_required: Optional[bool] = None
    notes: Optional[str] = None


class EventResponse(BaseModel):
    id: UUID
    name: str
    event_type: EventType
    client_name: str
    client_phone: str
    client_email: Optional[str] = None
    event_date: datetime
    venue: str
    guest_count: int
    status: EventStatus
    catering_required: bool
    decoration_required: bool
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BookingCreate(BaseModel):
    full_name: str
    phone: str
    email: Optional[str] = None
    event_type: EventType
    event_date: Optional[datetime] = None
    venue: Optional[str] = None
    guest_count: Optional[int] = None
    catering_required: bool = False
    decoration_required: bool = False
    special_requirements: Optional[str] = None


class BookingResponse(BaseModel):
    id: UUID
    full_name: str
    phone: str
    email: Optional[str] = None
    event_type: EventType
    event_date: Optional[datetime] = None
    venue: Optional[str] = None
    guest_count: Optional[int] = None
    status: BookingStatus
    created_at: datetime

    class Config:
        from_attributes = True


class StaffAssign(BaseModel):
    staff_id: UUID
    role: Optional[str] = None
