from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, Numeric, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import enum
from database import Base


class CategoryType(str, enum.Enum):
    vegetarian = "vegetarian"
    non_vegetarian = "non_vegetarian"
    wedding = "wedding"
    corporate = "corporate"
    buffet = "buffet"
    kerala_traditional = "kerala_traditional"


class MenuCategory(Base):
    __tablename__ = "menu_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category_type = Column(Enum(CategoryType), nullable=False)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)


class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(UUID(as_uuid=True), ForeignKey("menu_categories.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    is_vegetarian = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    price_per_person = Column(Numeric(10, 2), nullable=True)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
