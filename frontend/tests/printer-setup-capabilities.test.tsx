import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "../src/app";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("allows an operator to register the supported printer capabilities", async () => {
  const base = "http://localhost:8000/api/v1";
  const json = (body: unknown) => ({ ok: true, status: 200, headers: { get: () => "application/json" }, json: async () => body });
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/runtime-config.json") return json({ apiBaseUrl: base });
    if (url === `${base}/health`) return json({ status: "ok" });
    if (url === `${base}/config`) return json({ appName: "print-job-manager" });
    if (url === `${base}/queue`) return json({ jobs: [] });
    if (url === `${base}/cockpit`) return json({ activeJobs: [], failures: [], recentHistory: [] });
    if (url === `${base}/printers/printer-1` && init?.method === "PUT") return json({ id: "printer-1" });
    throw new Error(`Unexpected fetch: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /set up printer/i }));
  const printer = screen.getByRole("region", { name: /printer setup/i });
  fireEvent.change(within(printer).getByLabelText(/printer id/i), { target: { value: "printer-1" } });
  fireEvent.click(within(printer).getByRole("checkbox", { name: /enclosure/i }));
  fireEvent.click(within(printer).getByRole("checkbox", { name: /hardened nozzle/i }));
  fireEvent.change(within(printer).getByLabelText(/nozzle diameter/i), { target: { value: "0.4" } });
  for (const axis of ["x", "y", "z"]) {
    fireEvent.change(within(printer).getByLabelText(new RegExp(`build volume.*${axis}`, "i")), { target: { value: "200" } });
  }
  fireEvent.click(within(printer).getByRole("button", { name: /save printer/i }));

  await waitFor(() => {
    const call = fetchMock.mock.calls.find(([url]) => String(url) === `${base}/printers/printer-1`);
    expect(call).toBeDefined();
    expect(JSON.parse(String(call![1]?.body))).toMatchObject({
      enclosure: true,
      hardenedNozzle: true,
      nozzleDiameter: 0.4,
      buildVolume: { x: 200, y: 200, z: 200 },
    });
  });
});
