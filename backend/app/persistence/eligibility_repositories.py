from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from . import database, models


class SqlAlchemyPrinterCatalog:
    def add_printer(self, printer_id: str, enclosure: bool, hardened_nozzle: bool | None = None,
                    nozzle_diameter: float | None = None, build_volume: dict[str, float] | None = None) -> None:
        values = {
            "enclosure": enclosure, "hardened_nozzle": hardened_nozzle,
            "nozzle_diameter": nozzle_diameter,
            **{f"build_volume_{axis}": build_volume[axis] if build_volume else None for axis in ("x", "y", "z")},
        }
        statement = insert(models.PrinterCapabilityRecord).values(id=printer_id, **values)
        statement = statement.on_conflict_do_update(
            index_elements=[models.PrinterCapabilityRecord.id],
            set_=values,
        )
        with database.SessionFactory.begin() as session:
            session.execute(statement)

    def get_capabilities(self, printer_id: str) -> dict[str, object] | None:
        with database.SessionFactory() as session:
            printer = session.get(models.PrinterCapabilityRecord, printer_id)
            if printer is None:
                return None
            result = {"id": printer.id, "enclosure": printer.enclosure,
                      "hardenedNozzle": printer.hardened_nozzle, "nozzleDiameter": printer.nozzle_diameter}
            if printer.build_volume_x is not None:
                result["buildVolume"] = {"x": printer.build_volume_x, "y": printer.build_volume_y, "z": printer.build_volume_z}
            return result


class SqlAlchemyMaterialInventory:
    def add_material(self, material_type: str, color: str, amount_grams: float) -> int:
        with database.SessionFactory.begin() as session:
            material = models.InventoryMaterialRecord(
                material_type=material_type, color=color, amount_grams=amount_grams
            )
            session.add(material)
            session.flush()
            return material.id

    def correct_amount(self, material_id: int, amount_grams: float) -> bool:
        with database.SessionFactory.begin() as session:
            result = session.execute(
                update(models.InventoryMaterialRecord)
                .where(models.InventoryMaterialRecord.id == material_id)
                .values(amount_grams=amount_grams)
                .returning(models.InventoryMaterialRecord.id)
            )
            return result.scalar_one_or_none() is not None

    def is_available(self, material_type: str, color: str | None = None, amount_grams: float | None = None) -> bool:
        with database.SessionFactory() as session:
            query = select(models.InventoryMaterialRecord.id).where(
                models.InventoryMaterialRecord.material_type == material_type,
                models.InventoryMaterialRecord.amount_grams > 0,
            )
            if color is not None:
                query = query.where(models.InventoryMaterialRecord.color == color)
            if amount_grams is not None:
                query = query.where(models.InventoryMaterialRecord.amount_grams >= amount_grams)
            return session.scalar(query.limit(1)) is not None
