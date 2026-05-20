from pydantic import BaseModel

class ComponentConfig(BaseModel):
    ports: dict[str, int] = {}
    volumes: dict[str, str] = {}
    env: dict[str, str] = {}

class GenerateRequest(BaseModel):
    components: list[str]  # slugs
    config: dict[str, ComponentConfig] = {}
    include_sources: bool = True

class GenerateResponse(BaseModel):
    filename: str
    size_bytes: int
    files: list[str]
