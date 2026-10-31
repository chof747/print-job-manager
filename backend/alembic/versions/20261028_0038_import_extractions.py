"""Add import/extraction identity and typed extraction facts.

Revision ID: 20261028_0038
Revises: 20261028_0015
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261028_0038"
down_revision = "20261028_0015"
branch_labels = None
depends_on = None

SNAPSHOT_FLOATS = ("nozzle_diameter", "layer_height", "dimension_x", "dimension_y", "dimension_z")
SNAPSHOT_TEXTS = ("slicer", "printer_profile")
PROVENANCE_PREFIXES = ("nozzle", "layer", "dimensions", "slicer", "printer_profile")
EXECUTION_FLOATS = ("nozzle_diameter", "layer_height", "dimension_x", "dimension_y", "dimension_z")


def upgrade() -> None:
    op.add_column("artifacts", sa.Column("media_type", sa.Text(), nullable=False, server_default="application/octet-stream"))
    for table in ("artifacts", "jobs"):
        for name in SNAPSHOT_FLOATS:
            op.add_column(table, sa.Column(f"snapshot_{name}", sa.Float()))
        for name in SNAPSHOT_TEXTS:
            op.add_column(table, sa.Column(f"snapshot_{name}", sa.Text()))
        for prefix in PROVENANCE_PREFIXES:
            for suffix in ("parser", "source"):
                op.add_column(table, sa.Column(f"{prefix}_{suffix}", sa.Text()))
    for name in EXECUTION_FLOATS:
        op.add_column("jobs", sa.Column(f"execution_{name}", sa.Float()))
    for name in SNAPSHOT_TEXTS:
        op.add_column("jobs", sa.Column(f"execution_{name}", sa.Text()))

    op.create_table(
        "artifact_extractions",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("artifact_id", sa.String(255), sa.ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parser", sa.Text(), nullable=False),
        sa.Column("parser_version", sa.Text(), nullable=False, server_default="unknown"),
        sa.Column("has_extracted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("has_provenance", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("material", sa.Text()),
        sa.Column("filament_weight_grams", sa.Float()),
        sa.Column("estimated_duration", sa.Numeric()),
        *(sa.Column(name, sa.Float()) for name in SNAPSHOT_FLOATS),
        *(sa.Column(name, sa.Text()) for name in SNAPSHOT_TEXTS),
    )
    op.execute("""INSERT INTO artifact_extractions
        (id, artifact_id, parser, has_extracted, has_provenance, material, filament_weight_grams, estimated_duration)
        SELECT 'import:' || md5('legacy:' || id), id, 'gcode-metadata',
            snapshot_has_extracted, snapshot_has_provenance, snapshot_material, snapshot_weight, snapshot_duration
        FROM artifacts""")
    op.create_table(
        "artifact_imports",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("artifact_id", sa.String(255), sa.ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("extraction_id", sa.String(255), sa.ForeignKey("artifact_extractions.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("media_type", sa.Text(), nullable=False),
        sa.Column("position", sa.BigInteger(), sa.Identity(always=True), nullable=False, unique=True),
    )
    op.execute("""INSERT INTO artifact_imports (id, artifact_id, extraction_id, filename, media_type)
        SELECT 'legacy:' || id, id, 'import:' || md5('legacy:' || id), coalesce(filename, 'upload'), media_type FROM artifacts""")
    op.create_table(
        "extraction_provenance",
        sa.Column("extraction_id", sa.String(255), sa.ForeignKey("artifact_extractions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("field", sa.Text(), primary_key=True),
        sa.Column("parser", sa.Text(), nullable=False),
        sa.Column("source_key", sa.Text(), nullable=False),
        sa.CheckConstraint("field IN ('material', 'estimatedDuration', 'filamentWeightGrams', 'nozzleDiameter', 'layerHeight', 'dimensions', 'slicer', 'printerProfile')", name="ck_extraction_provenance_field"),
    )
    for field, prefix in (("material", "material"), ("estimatedDuration", "duration"), ("filamentWeightGrams", "weight")):
        op.execute(f"""INSERT INTO extraction_provenance (extraction_id, field, parser, source_key)
            SELECT 'import:' || md5('legacy:' || id), '{field}', {prefix}_parser, {prefix}_source
            FROM artifacts WHERE {prefix}_parser IS NOT NULL""")
    for table, extra_columns in (
        ("artifact_missing_planning_values", (sa.Column("planning_value", sa.Text(), nullable=False),)),
        ("artifact_diagnostics", (sa.Column("code", sa.Text(), nullable=False), sa.Column("source_key", sa.Text(), nullable=False))),
    ):
        op.create_table(
            table,
            sa.Column("artifact_id", sa.String(255), sa.ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False),
            sa.Column("extraction_id", sa.String(255), sa.ForeignKey("artifact_extractions.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("position", sa.Integer(), primary_key=True),
            *extra_columns,
        )
    op.execute("""INSERT INTO artifact_missing_planning_values (artifact_id, extraction_id, position, planning_value)
        SELECT id, 'import:' || md5('legacy:' || id), item.ordinality - 1, item.value
        FROM artifacts CROSS JOIN LATERAL unnest(missing_values) WITH ORDINALITY AS item(value, ordinality)""")
    op.execute("""INSERT INTO artifact_diagnostics (artifact_id, extraction_id, position, code, source_key)
        SELECT id, 'import:' || md5('legacy:' || id), item.ordinality - 1, item.code, item.source_key
        FROM artifacts CROSS JOIN LATERAL unnest(diagnostic_codes, diagnostic_sources)
        WITH ORDINALITY AS item(code, source_key, ordinality)""")
    for name in ("missing_values", "diagnostic_codes", "diagnostic_sources"):
        op.drop_column("artifacts", name)
    op.add_column("jobs", sa.Column("extraction_id", sa.String(255)))
    op.create_foreign_key("fk_job_extraction", "jobs", "artifact_extractions", ["extraction_id"], ["id"])
    op.execute("""UPDATE jobs SET extraction_id = (SELECT i.extraction_id FROM artifact_imports i
        WHERE i.artifact_id = jobs.artifact_ref ORDER BY i.position LIMIT 1)""")


def downgrade() -> None:
    op.drop_constraint("fk_job_extraction", "jobs", type_="foreignkey")
    op.drop_column("jobs", "extraction_id")
    for name in ("missing_values", "diagnostic_codes", "diagnostic_sources"):
        op.add_column("artifacts", sa.Column(name, postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"))
    # A legacy artifact has one snapshot; use its earliest import on downgrade.
    op.execute("""UPDATE artifacts a SET
        missing_values = ARRAY(SELECT v.planning_value FROM artifact_missing_planning_values v
            WHERE v.extraction_id = (SELECT i.extraction_id FROM artifact_imports i WHERE i.artifact_id = a.id ORDER BY i.position LIMIT 1) ORDER BY v.position),
        diagnostic_codes = ARRAY(SELECT d.code FROM artifact_diagnostics d
            WHERE d.extraction_id = (SELECT i.extraction_id FROM artifact_imports i WHERE i.artifact_id = a.id ORDER BY i.position LIMIT 1) ORDER BY d.position),
        diagnostic_sources = ARRAY(SELECT d.source_key FROM artifact_diagnostics d
            WHERE d.extraction_id = (SELECT i.extraction_id FROM artifact_imports i WHERE i.artifact_id = a.id ORDER BY i.position LIMIT 1) ORDER BY d.position)""")
    for table in ("artifact_diagnostics", "artifact_missing_planning_values", "extraction_provenance", "artifact_imports", "artifact_extractions"):
        op.drop_table(table)
    for name in EXECUTION_FLOATS + SNAPSHOT_TEXTS:
        op.drop_column("jobs", f"execution_{name}")
    for table in ("artifacts", "jobs"):
        for name in SNAPSHOT_FLOATS + SNAPSHOT_TEXTS:
            op.drop_column(table, f"snapshot_{name}")
        for prefix in PROVENANCE_PREFIXES:
            for suffix in ("parser", "source"):
                op.drop_column(table, f"{prefix}_{suffix}")
    op.drop_column("artifacts", "media_type")
