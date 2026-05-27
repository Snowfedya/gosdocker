from pydantic import BaseModel

class ComponentConfig(BaseModel):
    ports: dict[str, int] = {}
    volumes: dict[str, str] = {}
    env: dict[str, str] = {}

class GenerateRequest(BaseModel):
    components: list[str]  # slugs
    config: dict[str, ComponentConfig] = {}
    include_sources: bool = True
    security_profile: str = "basic"

    class Config:
        json_schema_extra = {
            "example": {
                "components": ["nginx", "postgresql"],
                "config": {
                    "nginx": {"ports": {"80": 80}},
                    "postgresql": {"env": {"POSTGRES_PASSWORD": "secret"}},
                },
                "security_profile": "standard",
            }
        }

class GenerateResponse(BaseModel):
    filename: str
    size_bytes: int
    files: list[str]
