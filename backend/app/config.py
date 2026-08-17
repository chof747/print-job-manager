import os


API_V1_PREFIX = "/api/v1"


def get_app_name() -> str:
    return os.environ.get("PRINT_JOB_MANAGER_APP_NAME", "print-job-manager")


def get_frontend_origin() -> str:
    return os.environ.get("PRINT_JOB_MANAGER_FRONTEND_ORIGIN", "http://localhost:5173")
