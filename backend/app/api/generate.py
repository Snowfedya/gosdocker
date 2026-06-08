import io
import yaml
import zipfile
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

    # Generate ZIP
    service = GenerateService()
    zip_buffer = service.create_zip(list(components), body.config)

    # Apply security profile: extract docker-compose.yml, apply profile, re-zip
    if body.security_profile != "basic":
        # Read existing zip
        in_bytes = zip_buffer.getvalue()
        new_buffer = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(in_bytes), 'r') as zin:
            with zipfile.ZipFile(new_buffer, 'w', zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    data = zin.read(item.filename)
                    if item.filename == "docker-compose.yml":
                        # Parse compose, apply security profile, re-dump
                        compose = yaml.safe_load(data)
                        compose = apply_profile(compose, body.security_profile)
                        comment_lines = [
                            l for l in data.decode("utf-8").split("\n")
                            if l.startswith("#") or l.strip() == ""
                        ]
                        header = "\n".join(comment_lines[:5]) + "\n"
                        # Anchor-free dumper (docker compose rejects &id / *id aliases)
                        class _NoAlias(yaml.SafeDumper):
                            pass
                        _NoAlias.add_representer(
                            dict,
                            lambda d, data: d.represent_mapping(
                                "tag:yaml.org,2002:map", data.items()
                            ),
                        )
                        new_data = header + yaml.dump(
                            compose, Dumper=_NoAlias, default_flow_style=False,
                            sort_keys=False, allow_unicode=True, indent=2
                        )
                        zout.writestr(item, new_data.encode("utf-8"))
                    else:
                        zout.writestr(item, data)
        new_buffer.seek(0)
        zip_buffer = new_buffer

    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=gosdocker-stack.zip"
        }
    )
