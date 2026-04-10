from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime
from jose import JWTError, jwt
from pydantic import BaseModel
from decimal import Decimal
from prometheus_fastapi_instrumentator import Instrumentator
import uuid
import random
import string

from database import get_db, init_db
from models import Invoice, Payment, InvoiceStatus
from config import settings

app = FastAPI(title="Billing Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)
bearer_scheme = HTTPBearer()


def require_auth(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    payload = require_auth(credentials)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return payload


class InvoiceCreate(BaseModel):
    event_id: Optional[uuid.UUID] = None
    client_name: str
    client_phone: str
    client_email: Optional[str] = None
    due_date: Optional[datetime] = None
    catering_cost: Decimal = Decimal("0")
    decoration_cost: Decimal = Decimal("0")
    rental_cost: Decimal = Decimal("0")
    staff_charges: Decimal = Decimal("0")
    tax_amount: Decimal = Decimal("0")
    discount_amount: Decimal = Decimal("0")
    notes: Optional[str] = None


class InvoiceUpdate(BaseModel):
    catering_cost: Optional[Decimal] = None
    decoration_cost: Optional[Decimal] = None
    rental_cost: Optional[Decimal] = None
    staff_charges: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    notes: Optional[str] = None
    due_date: Optional[datetime] = None


class PaymentCreate(BaseModel):
    amount: Decimal
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None


def generate_invoice_number() -> str:
    suffix = "".join(random.choices(string.digits, k=6))
    return f"SS-{datetime.now().year}-{suffix}"


def calculate_total(invoice: Invoice) -> Decimal:
    subtotal = (
        Decimal(str(invoice.catering_cost or 0))
        + Decimal(str(invoice.decoration_cost or 0))
        + Decimal(str(invoice.rental_cost or 0))
        + Decimal(str(invoice.staff_charges or 0))
    )
    total = subtotal + Decimal(str(invoice.tax_amount or 0)) - Decimal(str(invoice.discount_amount or 0))
    return subtotal, total


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "billing-service"}


@app.get("/api/invoices/")
async def list_invoices(db: AsyncSession = Depends(get_db), _: dict = Depends(require_auth)):
    result = await db.execute(select(Invoice).order_by(Invoice.created_at.desc()))
    return result.scalars().all()


@app.post("/api/invoices/", status_code=201)
async def create_invoice(data: InvoiceCreate, db: AsyncSession = Depends(get_db), _: dict = Depends(require_auth)):
    invoice = Invoice(
        invoice_number=generate_invoice_number(),
        **data.model_dump(),
    )
    subtotal, total = calculate_total(invoice)
    invoice.subtotal = subtotal
    invoice.total_amount = total
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    return invoice


@app.get("/api/invoices/{invoice_id}")
async def get_invoice(invoice_id: str, db: AsyncSession = Depends(get_db), _: dict = Depends(require_auth)):
    result = await db.execute(select(Invoice).where(Invoice.id == uuid.UUID(invoice_id)))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@app.put("/api/invoices/{invoice_id}")
async def update_invoice(invoice_id: str, update: InvoiceUpdate, db: AsyncSession = Depends(get_db), _: dict = Depends(require_auth)):
    result = await db.execute(select(Invoice).where(Invoice.id == uuid.UUID(invoice_id)))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(invoice, field, value)
    subtotal, total = calculate_total(invoice)
    invoice.subtotal = subtotal
    invoice.total_amount = total
    await db.commit()
    await db.refresh(invoice)
    return invoice


@app.put("/api/invoices/{invoice_id}/status")
async def update_status(invoice_id: str, status: InvoiceStatus, db: AsyncSession = Depends(get_db), _: dict = Depends(require_auth)):
    result = await db.execute(select(Invoice).where(Invoice.id == uuid.UUID(invoice_id)))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    invoice.status = status
    await db.commit()
    return {"message": "Status updated"}


@app.post("/api/invoices/{invoice_id}/payments", status_code=201)
async def add_payment(invoice_id: str, payment_data: PaymentCreate, db: AsyncSession = Depends(get_db), _: dict = Depends(require_auth)):
    result = await db.execute(select(Invoice).where(Invoice.id == uuid.UUID(invoice_id)))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    payment = Payment(invoice_id=uuid.UUID(invoice_id), **payment_data.model_dump())
    db.add(payment)
    invoice.status = InvoiceStatus.paid
    await db.commit()
    return {"message": "Payment recorded"}


@app.get("/api/billing/summary")
async def billing_summary(db: AsyncSession = Depends(get_db), _: dict = Depends(require_auth)):
    total = await db.execute(select(func.sum(Invoice.total_amount)).where(Invoice.status == InvoiceStatus.paid))
    pending = await db.execute(select(func.sum(Invoice.total_amount)).where(Invoice.status.in_([InvoiceStatus.sent, InvoiceStatus.draft])))
    count = await db.execute(select(func.count(Invoice.id)))
    return {
        "total_revenue": float(total.scalar() or 0),
        "pending_amount": float(pending.scalar() or 0),
        "total_invoices": count.scalar(),
    }


@app.get("/api/invoices/{invoice_id}/pdf")
async def download_pdf(invoice_id: str, db: AsyncSession = Depends(get_db), _: dict = Depends(require_auth)):
    result = await db.execute(select(Invoice).where(Invoice.id == uuid.UUID(invoice_id)))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    # PDF generation would use reportlab here
    return {"message": "PDF generation endpoint", "invoice_number": invoice.invoice_number}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=True)
