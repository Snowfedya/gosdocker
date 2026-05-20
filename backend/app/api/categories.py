from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, Integer
from ..database import get_db
from ..models import Category, Component
from ..schemas.category import CategoryResponse

router = APIRouter(prefix="/api/categories", tags=["categories"])

@router.get("", response_model=list[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    # Single query: categories with component counts
    query = (
        select(
            Category,
            func.count(Component.id).label("total"),
            func.sum(Component.is_registry.cast(Integer)).label("registry_count")
        )
        .outerjoin(Component, Category.id == Component.category_id)
        .group_by(Category.id)
        .order_by(Category.sort_order)
    )
    result = await db.execute(query)
    rows = result.all()

    return [
        CategoryResponse(
            id=cat.id,
            name=cat.name,
            slug=cat.slug,
            icon=cat.icon,
            description=cat.description,
            sort_order=cat.sort_order,
            components_count=total or 0,
            registry_count=registry_count or 0,
            community_count=(total or 0) - (registry_count or 0)
        )
        for cat, total, registry_count in rows
    ]
