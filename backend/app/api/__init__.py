from .categories import router as categories_router
from .components import router as components_router
from .stacks import router as stacks_router
from .generate import router as generate_router
from .registry import router as registry_router
from .constructor import router as constructor_router

__all__ = [
    "categories_router",
    "components_router",
    "stacks_router",
    "generate_router",
    "registry_router",
    "constructor_router",
]
