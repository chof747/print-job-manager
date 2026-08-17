from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1 import router as api_v1_router
from backend.app.config import get_app_name, get_frontend_origin
from backend.app.health import router as health_router


app = FastAPI(title=get_app_name())
app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_frontend_origin()],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(api_v1_router)
