from importlib import import_module


def test_inventory_matches_material_type_color_and_sufficient_amount() -> None:
    inventory_module = import_module("backend.app.inventory")
    inventory = inventory_module.MaterialInventory()
    inventory.add_material(material_type="PLA", color="black", amount_grams=100)

    assert inventory.is_available(material_type="PLA", color="black", amount_grams=100)
    assert not inventory.is_available(material_type="PETG", color="black", amount_grams=100)
    assert not inventory.is_available(material_type="PLA", color="white", amount_grams=100)
    assert not inventory.is_available(material_type="PLA", color="black", amount_grams=101)
