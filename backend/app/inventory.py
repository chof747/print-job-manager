from dataclasses import dataclass


@dataclass(frozen=True)
class Material:
    material_type: str
    color: str
    amount_grams: float


class MaterialInventory:
    def __init__(self) -> None:
        self._materials: list[Material] = []

    def add_material(self, material_type: str, color: str, amount_grams: float) -> None:
        self._materials.append(Material(material_type, color, amount_grams))

    def is_available(
        self, material_type: str, color: str | None = None, amount_grams: float | None = None
    ) -> bool:
        return any(
            material.material_type == material_type
            and material.amount_grams > 0
            and (color is None or material.color == color)
            and (amount_grams is None or material.amount_grams >= amount_grams)
            for material in self._materials
        )
