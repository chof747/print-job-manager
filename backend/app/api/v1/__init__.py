from fastapi import APIRouter

from ...config import API_V1_PREFIX
from . import health, jobs, root

router = APIRouter()
router.include_router(root.router, prefix=API_V1_PREFIX)
router.include_router(health.router, prefix=API_V1_PREFIX)
router.include_router(jobs.router, prefix=API_V1_PREFIX)
