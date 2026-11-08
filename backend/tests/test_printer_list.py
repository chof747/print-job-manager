from backend.app.api.v1 import jobs


def test_list_printers_uses_catalog(shell_client, monkeypatch):
    class Catalog:
        def list_printer_ids(self):
            return ["printer-a", "printer-b"]

    monkeypatch.setattr(jobs, "printer_catalog", Catalog())
    response = shell_client.get("/api/v1/printers")
    assert response.status_code == 200
    assert response.json() == ["printer-a", "printer-b"]
