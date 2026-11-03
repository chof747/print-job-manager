import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "../src/app";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("lets an operator slice the cockpit by maximum filament consumption", async () => {
  const base = "http://localhost:8000/api/v1";
  const job = (id: string) => ({
    id, state: "ready", version: 0,
    executionData: { artifactRef: id, artifactFilename: `${id}.gcode`, material: "PLA" },
    schedulingData: { priority: 0 },
  });
  const small = job("small");
  const large = job("large");
  const json = (body: unknown) => ({ ok: true, status: 200, headers: { get: () => "application/json" }, json: async () => body });
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/runtime-config.json") return json({ apiBaseUrl: base });
    if (url === `${base}/health`) return json({ status: "ok" });
    if (url === `${base}/config`) return json({ appName: "print-job-manager" });
    if (url === `${base}/queue`) return json({ jobs: [small, large] });
    if (url.startsWith(`${base}/cockpit`)) {
      const filtered = new URL(url).searchParams.get("maxFilamentWeightGrams") === "20";
      return json({ activeJobs: filtered ? [small] : [small, large], failures: [], recentHistory: [] });
    }
    throw new Error(`Unexpected fetch: ${url}`);
  }));

  render(<App />);
  await screen.findByText("large.gcode");
  fireEvent.change(screen.getByLabelText(/maximum filament (weight|consumption)/i), {
    target: { value: "20" },
  });
  fireEvent.click(screen.getByRole("button", { name: /apply filters/i }));

  const active = screen.getByRole("region", { name: /active/i });
  await within(active).findByText("small.gcode");
  expect(within(active).queryByText("large.gcode")).not.toBeInTheDocument();
});
