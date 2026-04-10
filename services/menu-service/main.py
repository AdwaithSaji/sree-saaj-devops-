from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from decimal import Decimal
from jose import JWTError, jwt
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
import uuid

from database import get_db, init_db
from models import MenuCategory, MenuItem, CategoryType
from config import settings

app = FastAPI(title="Menu Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)
bearer_scheme = HTTPBearer(auto_error=False)


def require_admin(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category_type: CategoryType
    display_order: int = 0


class ItemCreate(BaseModel):
    category_id: uuid.UUID
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_vegetarian: bool = True
    is_featured: bool = False
    price_per_person: Optional[Decimal] = None
    display_order: int = 0


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_vegetarian: Optional[bool] = None
    is_featured: Optional[bool] = None
    price_per_person: Optional[Decimal] = None
    is_active: Optional[bool] = None


@app.on_event("startup")
async def startup():
    await init_db()
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(MenuCategory))
        if not result.scalars().first():
            categories = [
                MenuCategory(name="Vegetarian Starters", description="Fresh vegetable-based starters", category_type=CategoryType.vegetarian, display_order=1),
                MenuCategory(name="Non-Vegetarian Main Course", description="Chicken, mutton & seafood dishes", category_type=CategoryType.non_vegetarian, display_order=2),
                MenuCategory(name="Wedding Special Menu", description="Traditional Kerala wedding menu", category_type=CategoryType.wedding, display_order=3),
                MenuCategory(name="Corporate Lunch Menu", description="Quick and nutritious corporate meals", category_type=CategoryType.corporate, display_order=4),
                MenuCategory(name="Grand Buffet", description="Unlimited buffet spread", category_type=CategoryType.buffet, display_order=5),
                MenuCategory(name="Kerala Sadya", description="Traditional Kerala sadya on banana leaf", category_type=CategoryType.kerala_traditional, display_order=6),
            ]
            db.add_all(categories)
            await db.flush()

            items = [
                MenuItem(category_id=categories[0].id, name="Vegetable Samosa", description="Crispy pastry filled with spiced potatoes and peas", is_vegetarian=True, is_featured=True, display_order=1),
                MenuItem(category_id=categories[0].id, name="Paneer Tikka", description="Marinated cottage cheese grilled to perfection", is_vegetarian=True, is_featured=True, display_order=2),
                MenuItem(category_id=categories[0].id, name="Mushroom 65", description="Spicy deep-fried mushrooms with curry leaves", is_vegetarian=True, display_order=3),
                MenuItem(category_id=categories[1].id, name="Chicken Curry", description="Traditional Kerala chicken curry with coconut milk", is_vegetarian=False, is_featured=True, display_order=1),
                MenuItem(category_id=categories[1].id, name="Mutton Biryani", description="Fragrant basmati rice with tender mutton", is_vegetarian=False, is_featured=True, display_order=2),
                MenuItem(category_id=categories[1].id, name="Fish Molee", description="Coconut milk fish curry — a Kerala classic", is_vegetarian=False, display_order=3),
                MenuItem(category_id=categories[2].id, name="Wedding Sadya Package", description="Full Kerala sadya with 24+ dishes", is_vegetarian=True, is_featured=True, price_per_person=Decimal("350"), display_order=1),
                MenuItem(category_id=categories[3].id, name="Corporate Lunch Box", description="Rice + 2 curries + salad + dessert", is_vegetarian=True, price_per_person=Decimal("150"), display_order=1),
                MenuItem(category_id=categories[4].id, name="Grand Buffet Package", description="Unlimited veg & non-veg spread — 30+ dishes", is_vegetarian=False, price_per_person=Decimal("450"), display_order=1),
                MenuItem(category_id=categories[5].id, name="Kerala Sadya", description="Full traditional sadya on banana leaf with 20+ dishes", is_vegetarian=True, is_featured=True, price_per_person=Decimal("300"), display_order=1),
                MenuItem(category_id=categories[5].id, name="Onam Sadya Special", description="Special Onam sadya with traditional payasam", is_vegetarian=True, is_featured=True, price_per_person=Decimal("400"), display_order=2),
            ]
            db.add_all(items)
            await db.commit()


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "menu-service"}


@app.get("/api/menu/categories")
async def list_categories(db: AsyncSession = Depends(get_db)):
    """Public endpoint."""
    result = await db.execute(
        select(MenuCategory).where(MenuCategory.is_active == True).order_by(MenuCategory.display_order)
    )
    return result.scalars().all()


@app.post("/api/menu/categories", status_code=201)
async def create_category(data: CategoryCreate, db: AsyncSession = Depends(get_db), _: dict = Depends(require_admin)):
    cat = MenuCategory(**data.model_dump())
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


@app.get("/api/menu/items")
async def list_items(category_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Public endpoint."""
    query = select(MenuItem).where(MenuItem.is_active == True)
    if category_id:
        query = query.where(MenuItem.category_id == uuid.UUID(category_id))
    query = query.order_by(MenuItem.display_order)
    result = await db.execute(query)
    return result.scalars().all()


@app.post("/api/menu/items", status_code=201)
async def create_item(data: ItemCreate, db: AsyncSession = Depends(get_db), _: dict = Depends(require_admin)):
    item = MenuItem(**data.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@app.get("/api/menu/items/{item_id}")
async def get_item(item_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MenuItem).where(MenuItem.id == uuid.UUID(item_id)))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.put("/api/menu/items/{item_id}")
async def update_item(item_id: str, update: ItemUpdate, db: AsyncSession = Depends(get_db), _: dict = Depends(require_admin)):
    result = await db.execute(select(MenuItem).where(MenuItem.id == uuid.UUID(item_id)))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await db.commit()
    await db.refresh(item)
    return item


@app.delete("/api/menu/items/{item_id}")
async def delete_item(item_id: str, db: AsyncSession = Depends(get_db), _: dict = Depends(require_admin)):
    result = await db.execute(select(MenuItem).where(MenuItem.id == uuid.UUID(item_id)))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.delete(item)
    await db.commit()
    return {"message": "Item deleted"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8006, reload=True)
