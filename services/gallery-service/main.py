from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from jose import JWTError, jwt
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
import uuid
import os
import aiofiles
import shutil
from pathlib import Path

from database import get_db, init_db
from models import GalleryImage, GalleryCategory
from config import settings

app = FastAPI(title="Gallery Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)
bearer_scheme = HTTPBearer(auto_error=False)

UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def require_auth(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> Optional[dict]:
    if not credentials:
        return None
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def require_admin(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "gallery-service"}


@app.get("/api/gallery/")
async def list_images(category: Optional[GalleryCategory] = None, db: AsyncSession = Depends(get_db)):
    """Public endpoint."""
    query = select(GalleryImage)
    if category:
        query = query.where(GalleryImage.category == category)
    query = query.order_by(GalleryImage.display_order, GalleryImage.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@app.get("/api/gallery/categories")
async def list_categories(db: AsyncSession = Depends(get_db)):
    """Public endpoint — returns categories with image counts."""
    result = await db.execute(
        select(GalleryImage.category, func.count(GalleryImage.id).label("count"))
        .group_by(GalleryImage.category)
    )
    return [{"category": row.category, "count": row.count} for row in result.all()]


@app.post("/api/gallery/", status_code=201)
async def upload_image(
    category: GalleryCategory = Form(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    is_featured: bool = Form(False),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = UPLOAD_DIR / filename

    async with aiofiles.open(filepath, "wb") as f:
        content = await file.read()
        await f.write(content)

    image_url = f"/uploads/{filename}"
    image = GalleryImage(
        title=title,
        description=description,
        category=category,
        image_url=image_url,
        thumbnail_url=image_url,
        is_featured=is_featured,
    )
    db.add(image)
    await db.commit()
    await db.refresh(image)
    return image


@app.delete("/api/gallery/{image_id}")
async def delete_image(image_id: str, db: AsyncSession = Depends(get_db), _: dict = Depends(require_admin)):
    result = await db.execute(select(GalleryImage).where(GalleryImage.id == uuid.UUID(image_id)))
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    # Remove file
    filepath = UPLOAD_DIR / image.image_url.split("/")[-1]
    if filepath.exists():
        filepath.unlink()
    await db.delete(image)
    await db.commit()
    return {"message": "Image deleted"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8005, reload=True)
