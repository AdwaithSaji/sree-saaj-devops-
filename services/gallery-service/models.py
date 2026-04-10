from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import enum
from database import Base


class GalleryCategory(str, enum.Enum):
    wedding = "wedding"
    birthday = "birthday"
    corporate = "corporate"
    catering = "catering"
    decoration = "decoration"
    other = "other"


class GalleryImage(Base):
    __tablename__ = "gallery_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    category = Column(Enum(GalleryCategory), nullable=False, default=GalleryCategory.other)
    image_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)
    is_featured = Column(Boolean, default=False)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
