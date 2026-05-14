"""Health route: ``/_health`` liveness probe used by Docker and load balancers."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/_health")
async def health() -> dict[str, str]:
    """Liveness probe used by Docker and load balancers."""
    return {"status": "ok"}
