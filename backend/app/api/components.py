from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pathlib import Path
from ..database import get_db
from ..models import Component, Category
from ..schemas.component import ComponentDetail
from app.services.slug import is_valid_slug

REGISTRY_DIR = Path(__file__).parent.parent.parent / "registry"


def _load_manifest_meta(slug: str) -> dict:
    """Load registry build info for a slug, or return empty.

    Defensive: even though slug comes from the DB (not user input), we
    validate it before constructing a filesystem path. If a malformed
    slug ever leaks into the DB, we'd rather return empty meta than
    raise.
    """
    import yaml
    if not is_valid_slug(slug):
        return {"has_registry": False, "build_method": None}
    manifest_path = REGISTRY_DIR / slug / "manifest.yml"
    if not manifest_path.exists():
        return {"has_registry": False, "build_method": None}
    try:
        data = yaml.safe_load(manifest_path.read_text())
        comp = data.get("component", {})
        return {
            "has_registry": True,
            "build_method": comp.get("build_method"),
        }
    except Exception:
        return {"has_registry": False, "build_method": None}

router = APIRouter(prefix="/api/components", tags=["components"])

@router.get("", response_model=list[ComponentDetail])
async def list_components(
    skip: int = 0,
    limit: int = 50,
    category: str | None = None,
    registry_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    query = select(Component).options(selectinload(Component.category))
    if category:
        query = query.join(Category).where(Category.slug == category)
    if registry_only:
        query = query.where(Component.is_registry == True)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    components = result.scalars().all()

    return [
        ComponentDetail(
            id=comp.id,
            name=comp.name,
            slug=comp.slug,
            category=comp.category.slug if comp.category else "",
            image=comp.image,
            is_registry=comp.is_registry,
            registry_number=comp.registry_number,
            image_source=comp.image_source or "",
            registry_url=comp.registry_url or "",
            description=comp.description,
            version=comp.version,
            default_ports=comp.default_ports or {},
            default_volumes=comp.default_volumes or {},
            default_env=comp.default_env or {},
            variables_schema=comp.variables_schema or {},
            has_registry=_load_manifest_meta(comp.slug)["has_registry"],
            build_method=_load_manifest_meta(comp.slug)["build_method"],
        )
        for comp in components
    ]

@router.get("/{slug}", response_model=ComponentDetail)
async def get_component(slug: str, db: AsyncSession = Depends(get_db)):
    query = select(Component).options(selectinload(Component.category)).where(Component.slug == slug)
    result = await db.execute(query)
    comp = result.scalar_one_or_none()

    if not comp:
        raise HTTPException(status_code=404, detail="Component not found")

    return ComponentDetail(
        id=comp.id,
        name=comp.name,
        slug=comp.slug,
        category=comp.category.slug if comp.category else "",
        image=comp.image,
        is_registry=comp.is_registry,
        registry_number=comp.registry_number,
        image_source=comp.image_source or "",
        registry_url=comp.registry_url or "",
        description=comp.description,
        version=comp.version,
        default_ports=comp.default_ports or {},
        default_volumes=comp.default_volumes or {},
        default_env=comp.default_env or {},
        variables_schema=comp.variables_schema or {},
        has_registry=_load_manifest_meta(comp.slug)["has_registry"],
        build_method=_load_manifest_meta(comp.slug)["build_method"],
    )
