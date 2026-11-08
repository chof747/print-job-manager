import importlib.util
from pathlib import Path

import pytest


@pytest.mark.parametrize("component", ["backend", "frontend"])
def test_image_suite_uses_supplied_prebuilt_image_without_building_or_removing_it(
    component: str, repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    filename = (
        "test_production_image.py"
        if component == "backend"
        else "test_frontend_production_image.py"
    )
    spec = importlib.util.spec_from_file_location(
        f"prebuilt_{component}_suite", repo_root / "backend" / "tests" / filename
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    image = f"example.test/{component}@sha256:{'a' * 64}"
    monkeypatch.setenv(f"PJM_{component.upper()}_IMAGE", image)

    def unexpected_docker(*args: object, **kwargs: object) -> None:
        pytest.fail("a supplied image must not be built or removed by the test suite")

    monkeypatch.setattr(module.subprocess, "run", unexpected_docker)
    fixture = getattr(module, f"{component}_image").__wrapped__(repo_root)
    try:
        assert next(fixture) == image
    finally:
        fixture.close()
