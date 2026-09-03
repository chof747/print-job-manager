from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

API_V1_PREFIX = "/api/v1"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PRINT_JOB_MANAGER_")

    app_name: str = "print-job-manager"
    frontend_origin: str = "http://localhost:5173"
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/print_job_manager"
    )
    artifact_storage_path: Path = Path("data/artifacts")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_app_name() -> str:
    return get_settings().app_name


def get_frontend_origin() -> str:
    return get_settings().frontend_origin
