import os

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware


API_V1_PREFIX = "/api/v1"
APP_NAME = os.environ.get("PRINT_JOB_MANAGER_APP_NAME", "print-job-manager")
FRONTEND_ORIGIN = os.environ.get(
    "PRINT_JOB_MANAGER_FRONTEND_ORIGIN", "http://localhost:5173"
)


app = FastAPI(title=APP_NAME)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
)
api_v1_router = APIRouter(prefix=API_V1_PREFIX)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def ready() -> dict[str, str]:
    return {"status": "ok"}


@api_v1_router.get("")
def api_v1() -> dict[str, str]:
    return {"status": "ok"}


@api_v1_router.get("/config")
def api_v1_config() -> dict[str, str]:
    return {
        "appName": app.title,
        "apiBasePath": API_V1_PREFIX,
    }


@api_v1_router.get("/health")
def api_v1_health() -> dict[str, str]:
    return health()


app.include_router(api_v1_router)
