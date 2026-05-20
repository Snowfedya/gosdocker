from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..models import Stack
from ..schemas.stack import StackResponse, StackComponentResponse

router = APIRouter(prefix="/api/stacks", tags=["stacks"])


@router.get("", response_model=list[StackResponse])
async def list_stacks(db: AsyncSession = Depends(get_db)):
    query = select(Stack).order_by(Stack.is_featured.desc())
    result = await db.execute(query)
    stacks = result.scalars().all()

    return [
        {
            "id": str(s.id),
            "name": s.name,
            "slug": s.slug,
            "description": s.description,
            "is_featured": s.is_featured,
            "components": [
                {"name": c.name, "slug": c.slug, "is_registry": c.is_registry}
                for c in s.components
            ]
        }
        for s in stacks
    ]

@router.get("/{slug}", response_model=StackResponse)
async def get_stack(slug: str, db: AsyncSession = Depends(get_db)):
    query = select(Stack).where(Stack.slug == slug)
    result = await db.execute(query)
    stack = result.scalar_one_or_none()

    if not stack:
        raise HTTPException(status_code=404, detail="Stack not found")

    return {
        "id": str(stack.id),
        "name": stack.name,
        "slug": stack.slug,
        "description": stack.description,
        "is_featured": stack.is_featured,
        "components": [
            {
                "name": c.name,
                "slug": c.slug,
                "is_registry": c.is_registry,
                "image": c.image,
                "registry_url": c.registry_url,
                "default_ports": c.default_ports or {},
                "default_env": c.default_env or {}
            }
            for c in stack.components
        ]
    }
