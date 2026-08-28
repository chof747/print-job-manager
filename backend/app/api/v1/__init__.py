from fastapi import APIRouter

from backend.app.api.v1 import health, jobs, root
from backend.app.config import API_V1_PREFIX


router = APIRouter()
router.include_router(root.router, prefix=API_V1_PREFIX)
router.include_router(health.router, prefix=API_V1_PREFIX)
router.include_router(jobs.router, prefix=API_V1_PREFIX)
