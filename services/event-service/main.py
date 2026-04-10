from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime
from typing import Optional
from jose import JWTError, jwt
from prometheus_fastapi_instrumentator import Instrumentator
import uuid

from database import get_db, init_db
from models import Event, EventStaff, BookingInquiry, EventStatus, EventType
from schemas import (
    EventCreate, EventUpdate, EventResponse,
    BookingCreate, BookingResponse, StaffAssign
)
from config import settings

app = FastAPI(title="Event Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)
bearer_scheme = HTTPBearer(auto_error=False)


def get_token_payload(credentials: Optional[HTTPAuthorizationCredentials]) -> Optional[dict]:
    if not credentials:
        return None
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def require_auth(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    payload = get_token_payload(credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Authentication required")
    return payload


def require_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    payload = require_auth(credentials)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return payload


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "event-service"}


# ── Events ──────────────────────────────────────────────────────────────────

@app.get("/api/events/", response_model=list[EventResponse])
async def list_events(
    status: Optional[EventStatus] = None,
    event_type: Optional[EventType] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    query = select(Event)
    filters = []
    if status:
        filters.append(Event.status == status)
    if event_type:
        filters.append(Event.event_type == event_type)
    if date_from:
        filters.append(Event.event_date >= date_from)
    if date_to:
        filters.append(Event.event_date <= date_to)
    if filters:
        query = query.where(and_(*filters))
    query = query.order_by(Event.event_date.desc())
    result = await db.execute(query)
    return result.scalars().all()


@app.post("/api/events/", response_model=EventResponse, status_code=201)
async def create_event(
    event_data: EventCreate,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(require_auth),
):
    event = Event(**event_data.model_dump(), created_by=uuid.UUID(token["sub"]))
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@app.get("/api/events/calendar", response_model=list[EventResponse])
async def get_calendar(
    month: int = Query(default=datetime.now().month, ge=1, le=12),
    year: int = Query(default=datetime.now().year),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    from_date = datetime(year, month, 1)
    if month == 12:
        to_date = datetime(year + 1, 1, 1)
    else:
        to_date = datetime(year, month + 1, 1)
    result = await db.execute(
        select(Event).where(
            and_(Event.event_date >= from_date, Event.event_date < to_date)
        ).order_by(Event.event_date)
    )
    return result.scalars().all()


@app.get("/api/events/{event_id}", response_model=EventResponse)
async def get_event(event_id: str, db: AsyncSession = Depends(get_db), _: dict = Depends(require_auth)):
    result = await db.execute(select(Event).where(Event.id == uuid.UUID(event_id)))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@app.put("/api/events/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: str,
    update: EventUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    result = await db.execute(select(Event).where(Event.id == uuid.UUID(event_id)))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(event, field, value)
    await db.commit()
    await db.refresh(event)
    return event


@app.delete("/api/events/{event_id}")
async def delete_event(event_id: str, db: AsyncSession = Depends(get_db), _: dict = Depends(require_admin)):
    result = await db.execute(select(Event).where(Event.id == uuid.UUID(event_id)))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    await db.delete(event)
    await db.commit()
    return {"message": "Event deleted"}


@app.post("/api/events/{event_id}/staff", status_code=201)
async def assign_staff(
    event_id: str,
    assignment: StaffAssign,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    result = await db.execute(select(Event).where(Event.id == uuid.UUID(event_id)))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Event not found")
    es = EventStaff(event_id=uuid.UUID(event_id), staff_id=assignment.staff_id, role=assignment.role)
    db.add(es)
    await db.commit()
    return {"message": "Staff assigned"}


@app.get("/api/events/{event_id}/staff")
async def get_event_staff(event_id: str, db: AsyncSession = Depends(get_db), _: dict = Depends(require_auth)):
    result = await db.execute(select(EventStaff).where(EventStaff.event_id == uuid.UUID(event_id)))
    return result.scalars().all()


# ── Bookings ─────────────────────────────────────────────────────────────────

@app.post("/api/bookings/", response_model=BookingResponse, status_code=201)
async def create_booking(booking_data: BookingCreate, db: AsyncSession = Depends(get_db)):
    """Public endpoint — no auth required."""
    booking = BookingInquiry(**booking_data.model_dump())
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return booking


@app.get("/api/bookings/", response_model=list[BookingResponse])
async def list_bookings(db: AsyncSession = Depends(get_db), _: dict = Depends(require_auth)):
    result = await db.execute(select(BookingInquiry).order_by(BookingInquiry.created_at.desc()))
    return result.scalars().all()


@app.put("/api/bookings/{booking_id}/status")
async def update_booking_status(
    booking_id: str,
    status: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    result = await db.execute(select(BookingInquiry).where(BookingInquiry.id == uuid.UUID(booking_id)))
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.status = status
    await db.commit()
    return {"message": "Status updated"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
