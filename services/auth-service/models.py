import uuid
import enum
from sqlalchemy import Column, String, Boolean, DateTime, func
from database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    staff = "staff"


class User(Base):
    __tablename__ = "users"

    id           = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email        = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name    = Column(String(255), nullable=False)
    role         = Column(String(20),  nullable=False, default=UserRole.staff)
    phone        = Column(String(20),  nullable=True)
    is_active    = Column(Boolean,     default=True)
    created_at   = Column(DateTime,    server_default=func.now())
