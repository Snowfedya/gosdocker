from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..models import Component
from ..schemas.generate import GenerateRequest
from ..services.generate_service import GenerateService

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

    # Generate ZIP
    service = GenerateService()
    zip_buffer = service.create_zip(list(components), body.config)

    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=gosdocker-stack.zip"
        }
    )
