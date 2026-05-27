from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..models import Component
from ..schemas.generate import GenerateRequest
from ..services.generate_service import GenerateService
from ..services.security_profiles import apply_profile

router = APIRouter(prefix="/api/generate", tags=["generate"])


@router.post("")
async def generate_compose(
    body: GenerateRequest,
    db: AsyncSession = Depends(get_db)
):
    # Get components
    query = select(Component).where(Component.slug.in_(body.components))
    result = await db.execute(query)
    components = result.scalars().all()

    if not components:
        raise HTTPException(status_code=404, detail="No components found")

    # Generate ZIP (legacy — still works for old clients)
    service = GenerateService()
    zip_buffer = service.create_zip(list(components), body.config)

    # If a non-basic security profile is requested, we'd need to post-process
    # For now, body.security_profile is noted for backward compat
    # The new constructor endpoint (/api/constructor) handles profiles fully

    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=gosdocker-stack.zip"
        }
    )
