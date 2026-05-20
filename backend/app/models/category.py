from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from ..database import Base

def _utcnow() -> datetime:
    return datetime.utcnow()

class Category(Base):
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    icon = Column(String(50), default="📦")
    description = Column(Text)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow)

    components = relationship("Component", back_populates="category", lazy="selectin")
