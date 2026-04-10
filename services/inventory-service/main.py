from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from jose import JWTError, jwt
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
import uuid

from database import get_db, init_db
from models import InventoryItem, EventInventory, ItemCategory
from config import settings

app = FastAPI(title="Inventory Service", version="1.0.0")

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


# Schemas
class ItemCreate(BaseModel):
    name: str
    category: ItemCategory
    total_quantity: int
    available_quantity: int
    unit: str = "pieces"
    min_threshold: int = 10
    notes: Optional[str] = None


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    total_quantity: Optional[int] = None
    available_quantity: Optional[int] = None
    damaged_quantity: Optional[int] = None
    min_threshold: Optional[int] = None
    notes: Optional[str] = None


class EventItemAssign(BaseModel):
    inventory_item_id: uuid.UUID
    quantity_taken: int
    notes: Optional[str] = None


class EventItemUpdate(BaseModel):
    quantity_returned: Optional[int] = None
    quantity_damaged: Optional[int] = None
    notes: Optional[str] = None


@app.on_event("startup")
async def startup():
    await init_db()
    # Seed initial inventory
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(InventoryItem))
        if not result.scalars().first():
            seed_items = [
                InventoryItem(name="Dinner Plates", category=ItemCategory.plates, total_quantity=500, available_quantity=500, unit="pieces", min_threshold=50),
                InventoryItem(name="Side Plates", category=ItemCategory.plates, total_quantity=300, available_quantity=300, unit="pieces", min_threshold=30),
                InventoryItem(name="Water Glasses", category=ItemCategory.glasses, total_quantity=400, available_quantity=400, unit="pieces", min_threshold=40),
                InventoryItem(name="Juice Glasses", category=ItemCategory.glasses, total_quantity=200, available_quantity=200, unit="pieces", min_threshold=20),
                InventoryItem(name="Curry Bowls", category=ItemCategory.bowls, total_quantity=300, available_quantity=300, unit="pieces", min_threshold=30),
                InventoryItem(name="Plastic Chairs", category=ItemCategory.chairs, total_quantity=200, available_quantity=200, unit="pieces", min_threshold=20),
                InventoryItem(name="Steel Tables", category=ItemCategory.tables, total_quantity=50, available_quantity=50, unit="pieces", min_threshold=5),
                InventoryItem(name="Flower Decorations", category=ItemCategory.decorations, total_quantity=100, available_quantity=100, unit="sets", min_threshold=10),
            ]
            db.add_all(seed_items)
            await db.commit()


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "inventory-service"}


@app.get("/api/inventory/")
async def list_items(
    category: Optional[ItemCategory] = None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    query = select(InventoryItem)
    if category:
        query = query.where(InventoryItem.category == category)
    result = await db.execute(query.order_by(InventoryItem.category, InventoryItem.name))
    return result.scalars().all()


@app.post("/api/inventory/", status_code=201)
async def add_item(item_data: ItemCreate, db: AsyncSession = Depends(get_db), _: dict = Depends(require_admin)):
    item = InventoryItem(**item_data.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@app.get("/api/inventory/low-stock")
async def low_stock(db: AsyncSession = Depends(get_db), _: dict = Depends(require_auth)):
    result = await db.execute(
        select(InventoryItem).where(InventoryItem.available_quantity <= InventoryItem.min_threshold)
    )
    return result.scalars().all()


@app.get("/api/inventory/{item_id}")
async def get_item(item_id: str, db: AsyncSession = Depends(get_db), _: dict = Depends(require_auth)):
    result = await db.execute(select(InventoryItem).where(InventoryItem.id == uuid.UUID(item_id)))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.put("/api/inventory/{item_id}")
async def update_item(item_id: str, update: ItemUpdate, db: AsyncSession = Depends(get_db), _: dict = Depends(require_admin)):
    result = await db.execute(select(InventoryItem).where(InventoryItem.id == uuid.UUID(item_id)))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await db.commit()
    await db.refresh(item)
    return item


@app.delete("/api/inventory/{item_id}")
async def delete_item(item_id: str, db: AsyncSession = Depends(get_db), _: dict = Depends(require_admin)):
    result = await db.execute(select(InventoryItem).where(InventoryItem.id == uuid.UUID(item_id)))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.delete(item)
    await db.commit()
    return {"message": "Item deleted"}


@app.post("/api/inventory/events/{event_id}/assign", status_code=201)
async def assign_to_event(event_id: str, assignment: EventItemAssign, db: AsyncSession = Depends(get_db), _: dict = Depends(require_auth)):
    item_result = await db.execute(select(InventoryItem).where(InventoryItem.id == assignment.inventory_item_id))
    item = item_result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    if item.available_quantity < assignment.quantity_taken:
        raise HTTPException(status_code=400, detail=f"Only {item.available_quantity} available")

    item.available_quantity -= assignment.quantity_taken
    ei = EventInventory(
        event_id=uuid.UUID(event_id),
        inventory_item_id=assignment.inventory_item_id,
        quantity_taken=assignment.quantity_taken,
        notes=assignment.notes,
    )
    db.add(ei)
    await db.commit()
    return {"message": "Items assigned to event"}


@app.get("/api/inventory/events/{event_id}")
async def get_event_inventory(event_id: str, db: AsyncSession = Depends(get_db), _: dict = Depends(require_auth)):
    result = await db.execute(select(EventInventory).where(EventInventory.event_id == uuid.UUID(event_id)))
    return result.scalars().all()


@app.put("/api/inventory/events/{event_id}/{assignment_id}")
async def update_event_inventory(
    event_id: str,
    assignment_id: str,
    update: EventItemUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    result = await db.execute(select(EventInventory).where(EventInventory.id == uuid.UUID(assignment_id)))
    ei = result.scalar_one_or_none()
    if not ei:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if update.quantity_returned is not None:
        item_result = await db.execute(select(InventoryItem).where(InventoryItem.id == ei.inventory_item_id))
        item = item_result.scalar_one()
        returned_diff = update.quantity_returned - ei.quantity_returned
        item.available_quantity += returned_diff
        ei.quantity_returned = update.quantity_returned

    if update.quantity_damaged is not None:
        ei.quantity_damaged = update.quantity_damaged
    if update.notes is not None:
        ei.notes = update.notes

    await db.commit()
    return {"message": "Updated"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True)
