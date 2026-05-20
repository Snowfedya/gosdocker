from pydantic import BaseModel
from uuid import UUID

class CategoryBase(BaseModel):
    name: str
    slug: str
    icon: str = "📦"
    description: str | None = None
    sort_order: int = 0

class CategoryResponse(CategoryBase):
    id: UUID
    components_count: int = 0
    registry_count: int = 0
    community_count: int = 0

    class Config:
        from_attributes = True
