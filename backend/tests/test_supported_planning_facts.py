import pytest

from backend.app.persistence.models import JobRecord


def test_explicit_nozzle_diameter_round_trips() -> None:
    record = JobRecord(artifact_ref="artifact")
    record.execution_data = {
        "artifactRef": "artifact",
        "material": "PLA",
        "nozzleDiameter": 0.4,
    }
    assert record.execution_data == {
        "artifactRef": "artifact",
        "material": "PLA",
        "nozzleDiameter": 0.4,
    }


@pytest.mark.parametrize("value", [60, {"nested": [1, 2]}])
def test_unknown_new_planning_facts_are_rejected(value: object) -> None:
    record = JobRecord(artifact_ref="artifact")
    with pytest.raises(ValueError, match="Unsupported planning facts: custom"):
        record.execution_data = {"artifactRef": "artifact", "custom": value}
