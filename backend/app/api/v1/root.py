from fastapi import APIRouter

from backend.app.config import API_V1_PREFIX, get_app_name


router = APIRouter()


@router.get("")
def root() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/config")
def config() -> dict[str, str]:
    return {
        "appName": get_app_name(),
        "apiBasePath": API_V1_PREFIX,
    }
