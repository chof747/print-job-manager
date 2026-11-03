from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_scheduling_migrations_upgrade_from_extraction_prerequisite_head(
    repo_root: Path,
) -> None:
    config = Config(str(repo_root / "backend" / "alembic.ini"))
    config.set_main_option("script_location", str(repo_root / "backend" / "alembic"))
    scripts = ScriptDirectory.from_config(config)

    # Revision 0038 is the head containing issue #60's relational extractions.
    revisions = list(scripts.iterate_revisions("head", "20261028_0038"))

    assert revisions, "scheduling changes must migrate forward from the prerequisite schema"
