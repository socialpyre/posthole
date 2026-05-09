from fastapi import APIRouter

router = APIRouter()


@router.get("/_health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
