import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "../src/app";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("sets up printer and material facts before checking job eligibility", async () => {
  const base = "http://localhost:8000/api/v1";
  const job = {
    id: "job-1", state: "ready", version: 0,
    executionData: { artifactRef: "artifact-1", artifactFilename: "part.gcode", material: "PLA" },
    schedulingData: { priority: 0 },
  };
  const json = (body: unknown, status = 200) => ({
    ok: status >= 200 && status < 300, status,
    headers: { get: () => "application/json" }, json: async () => body,
  });
  let printerSaved = false;
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/runtime-config.json") return json({ apiBaseUrl: base });
    if (url === `${base}/health`) return json({ status: "ok" });
    if (url === `${base}/config`) return json({ appName: "print-job-manager" });
    if (url === `${base}/queue`) return json({ jobs: [job] });
    if (url === `${base}/cockpit`) return json({ activeJobs: [job], failures: [], recentHistory: [] });
    if (url === `${base}/jobs/job-1`) return json(job);
    if (url === `${base}/printers`) return json(printerSaved ? ["printer-1"] : []);
    if (url === `${base}/printers/printer-1` && init?.method === "PUT") {
      printerSaved = true;
      return json({ id: "printer-1", enclosure: true });
    }
    if (url === `${base}/inventory/materials` && init?.method === "POST") return json({ id: 1, materialType: "PLA", color: "black", amountGrams: 100 }, 201);
    if (url === `${base}/jobs/job-1/eligibility` && init?.method === "POST") return json({ eligible: true, blocked: false, failures: [], satisfied: [{ code: "material_satisfied" }] });
    throw new Error(`Unexpected fetch: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /set up printer/i }));
  const printer = screen.getByRole("region", { name: /printer setup/i });
  fireEvent.change(within(printer).getByLabelText(/printer id/i), { target: { value: "printer-1" } });
  fireEvent.click(within(printer).getByRole("checkbox", { name: /enclosure/i }));
  fireEvent.click(within(printer).getByRole("button", { name: /save printer/i }));
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(`${base}/printers/printer-1`, expect.objectContaining({ method: "PUT" })));
  fireEvent.click(screen.getByRole("button", { name: "Close" }));

  fireEvent.click(screen.getByRole("button", { name: /add material/i }));
  const inventory = screen.getByRole("region", { name: /material setup/i });
  fireEvent.change(within(inventory).getByLabelText(/material type/i), { target: { value: "PLA" } });
  fireEvent.change(within(inventory).getByLabelText(/color/i), { target: { value: "black" } });
  fireEvent.change(within(inventory).getByLabelText(/amount/i), { target: { value: "100" } });
  fireEvent.click(within(inventory).getByRole("button", { name: /save material/i }));
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(`${base}/inventory/materials`, expect.objectContaining({ method: "POST" })));
  fireEvent.click(screen.getByRole("button", { name: "Close" }));

  const active = await screen.findByRole("region", { name: /active/i });
  fireEvent.click(within(active).getByRole("button", { name: /details/i }));
  const details = await screen.findByRole("region", { name: /job details/i });
  await within(details).findByRole("option", { name: "printer-1" });
  fireEvent.change(within(details).getByLabelText(/printer id/i), { target: { value: "printer-1" } });
  fireEvent.click(within(details).getByRole("button", { name: /check eligibility/i }));
  expect(await screen.findByRole("dialog", { name: "Job eligible" })).toBeVisible();
});
