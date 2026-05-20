from sqlalchemy import Column, String, Text, Boolean, DateTime, Table, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from ..database import Base

def _utcnow() -> datetime:
    return datetime.utcnow()

stack_components = Table(
    'stack_components',
    Base.metadata,
    Column('stack_id', UUID(as_uuid=True), ForeignKey('stacks.id')),
    Column('component_id', UUID(as_uuid=True), ForeignKey('components.id'))
)

class Stack(Base):
    __tablename__ = "stacks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False)
    description = Column(Text)
    is_featured = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)

    components = relationship("Component", secondary=stack_components, lazy="selectin")
