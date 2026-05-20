from pydantic import BaseModel


class StackComponentResponse(BaseModel):
    name: str
    slug: str
    is_registry: bool
    image: str | None = None
    registry_url: str | None = None
    default_ports: dict | None = None
    default_env: dict | None = None


class StackResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None = None
    is_featured: bool
    components: list[StackComponentResponse]

    class Config:
        from_attributes = True