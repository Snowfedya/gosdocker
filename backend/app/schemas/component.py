from pydantic import BaseModel, ConfigDict
from uuid import UUID

class ComponentBase(BaseModel):
    name: str
    slug: str
    image: str
    is_registry: bool = False
    registry_number: str | None = None
    description: str | None = None
    version: str | None = None

class ComponentDetail(ComponentBase):
    id: UUID
    category: str
    image_source: str
    registry_url: str
    default_ports: dict = {}
    default_volumes: dict = {}
    default_env: dict = {}
    variables_schema: dict = {}
    has_registry: bool = False
    build_method: str | None = None

    model_config = ConfigDict(from_attributes=True)
