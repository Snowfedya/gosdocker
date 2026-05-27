import logging
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from .api import categories_router, components_router, stacks_router, generate_router, registry_router, constructor_router
from .database import get_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI(
    title="GosDocker API",
    description="Каталог Docker Compose-сборок для госструктур",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://gosdocker.ru",
        "http://gosdocker.ru",
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(categories_router)
app.include_router(components_router)
app.include_router(stacks_router)
app.include_router(generate_router)
app.include_router(registry_router)
app.include_router(constructor_router)

@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail={"status": "error", "db": str(e)})
