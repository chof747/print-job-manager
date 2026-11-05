"""Generate the scheduling client from the current FastAPI OpenAPI schema."""

import json
import subprocess
import tempfile
from pathlib import Path

from backend.app.main import app

schema = app.openapi()
paths = ("/api/v1/jobs/{job_id}/scheduling", "/api/v1/cockpit", "/api/v1/jobs/{job_id}")
schema["paths"] = {path.removeprefix("/api/v1"): schema["paths"][path] for path in paths}
schemas = schema["components"]["schemas"]
referenced = set()


def collect_refs(value):
    if isinstance(value, dict):
        ref = value.get("$ref", "")
        if ref.startswith("#/components/schemas/"):
            name = ref.rsplit("/", 1)[-1]
            if name not in referenced:
                referenced.add(name)
                collect_refs(schemas[name])
        for child in value.values():
            collect_refs(child)
    elif isinstance(value, list):
        for child in value:
            collect_refs(child)


collect_refs(schema["paths"])
schema["components"]["schemas"] = {name: schemas[name] for name in sorted(referenced)}
for model in schema["components"]["schemas"].values():
    # This generator discards named properties when additionalProperties is true.
    # Omitting it retains OpenAPI's default of allowing additional properties.
    if model.get("properties") and model.get("additionalProperties") is True:
        del model["additionalProperties"]

with tempfile.TemporaryDirectory() as directory:
    schema_path = Path(directory) / "openapi.json"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")
    subprocess.run(
        [
            "pnpm", "exec", "openapi", "--input", str(schema_path),
            "--output", "frontend/src/generated/scheduling", "--client", "fetch",
            "--useOptions", "--useUnionTypes", "--name", "SchedulingClient",
        ],
        check=True,
    )
