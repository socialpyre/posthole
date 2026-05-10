"""System routes: health, readiness, and other infrastructure endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/_health")
async def health() -> dict[str, str]:
    """Liveness probe used by Docker and load balancers."""
    return {"status": "ok"}
