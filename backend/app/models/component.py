from sqlalchemy import Column, String, Text, Boolean, ForeignKey, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from ..database import Base

def _utcnow() -> datetime:
    return datetime.utcnow()

class Component(Base):
    __tablename__ = "components"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"))

    # Docker
    image = Column(String(500), nullable=False)
    image_source = Column(String(200))  # "registry.red-soft.ru" / "dh-mirror.gitverse.ru"
    registry_url = Column(String(500), nullable=False)
    is_registry = Column(Boolean, default=False)
    registry_number = Column(String(50))  # "№17604"

    # Метаданные
    description = Column(Text)
    version = Column(String(50))
    documentation_url = Column(String(500))

    # Конфигурация
    default_ports = Column(JSON, default=dict)
    default_volumes = Column(JSON, default=dict)
    default_env = Column(JSON, default=dict)
    variables_schema = Column(JSON, default=dict)
    template_file = Column(String(500))

    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    category = relationship("Category", back_populates="components", lazy="selectin")
