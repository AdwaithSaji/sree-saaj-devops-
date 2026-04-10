from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from prometheus_fastapi_instrumentator import Instrumentator
from jose import JWTError, jwt
import httpx
import logging
from typing import Optional

from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Sree Saaj API Gateway", version="1.0.0", docs_url="/api/docs", redoc_url="/api/redoc")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)
bearer_scheme = HTTPBearer(auto_error=False)

# Public paths that don't require auth
PUBLIC_PATHS = {
    "/api/auth/login",
    "/api/auth/refresh",
    "/api/bookings/",
    "/api/gallery/",
    "/api/gallery/categories",
    "/api/menu/categories",
    "/api/menu/items",
    "/health",
    "/api/docs",
    "/api/redoc",
    "/openapi.json",
}

SERVICE_MAP = {
    "/api/auth": settings.AUTH_SERVICE_URL,
    "/api/events": settings.EVENT_SERVICE_URL,
    "/api/bookings": settings.EVENT_SERVICE_URL,
    "/api/inventory": settings.INVENTORY_SERVICE_URL,
    "/api/invoices": settings.BILLING_SERVICE_URL,
    "/api/billing": settings.BILLING_SERVICE_URL,
    "/api/gallery": settings.GALLERY_SERVICE_URL,
    "/api/menu": settings.MENU_SERVICE_URL,
}


def is_public(path: str) -> bool:
    for pub in PUBLIC_PATHS:
        if path.startswith(pub.rstrip("/")):
            return True
    return False


def get_target_url(path: str) -> Optional[str]:
    for prefix, base_url in SERVICE_MAP.items():
        if path.startswith(prefix):
            return base_url + path
    return None


@app.get("/health")
async def health():
    async with httpx.AsyncClient(timeout=3.0) as client:
        services = {
            "auth": settings.AUTH_SERVICE_URL + "/health",
            "event": settings.EVENT_SERVICE_URL + "/health",
            "inventory": settings.INVENTORY_SERVICE_URL + "/health",
            "billing": settings.BILLING_SERVICE_URL + "/health",
            "gallery": settings.GALLERY_SERVICE_URL + "/health",
            "menu": settings.MENU_SERVICE_URL + "/health",
        }
        statuses = {}
        for name, url in services.items():
            try:
                resp = await client.get(url)
                statuses[name] = "healthy" if resp.status_code == 200 else "unhealthy"
            except Exception:
                statuses[name] = "unreachable"

    overall = "healthy" if all(v == "healthy" for v in statuses.values()) else "degraded"
    return {"status": overall, "services": statuses}


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@limiter.limit("200/minute")
async def proxy(request: Request, path: str):
    full_path = f"/api/{path}"
    target_url = get_target_url(full_path)

    if not target_url:
        raise HTTPException(status_code=404, detail="Route not found")

    # Auth check for protected routes
    if not is_public(full_path):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Authentication required")
        token = auth_header.split(" ")[1]
        try:
            jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Build query string
    query_string = str(request.url.query)
    if query_string:
        target_url = f"{target_url}?{query_string}"

    # Forward request
    headers = dict(request.headers)
    headers.pop("host", None)
    body = await request.body()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
            )
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Service temporarily unavailable")
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Service timeout")

    logger.info(f"{request.method} {full_path} → {response.status_code}")

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.headers.get("content-type"),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
