class PrinterCatalog:
    def __init__(self) -> None:
        self._printers: dict[str, dict[str, object]] = {}

    def add_printer(self, printer_id: str, enclosure: bool) -> None:
        self._printers[printer_id] = {"id": printer_id, "enclosure": enclosure}

    def get_capabilities(self, printer_id: str) -> dict[str, object] | None:
        printer = self._printers.get(printer_id)
        return printer.copy() if printer is not None else None
