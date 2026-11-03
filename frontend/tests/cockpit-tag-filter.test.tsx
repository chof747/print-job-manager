import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "../src/app";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("lets an operator slice the cockpit by tag", async () => {
  const base = "http://localhost:8000/api/v1";
  const job = (id: string) => ({
    id, state: "ready", version: 0,
    executionData: { artifactRef: id, artifactFilename: `${id}.gcode`, material: "PLA" },
    schedulingData: { priority: 0 },
  });
  const matching = job("matching");
  const other = job("other");
  const json = (body: unknown) => ({ ok: true, status: 200, headers: { get: () => "application/json" }, json: async () => body });
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/runtime-config.json") return json({ apiBaseUrl: base });
    if (url === `${base}/health`) return json({ status: "ok" });
    if (url === `${base}/config`) return json({ appName: "print-job-manager" });
    if (url === `${base}/queue`) return json({ jobs: [matching, other] });
    if (url.startsWith(`${base}/cockpit`)) {
      const filtered = new URL(url).searchParams.get("tag") === "urgent";
      return json({ activeJobs: filtered ? [matching] : [matching, other], failures: [], recentHistory: [] });
    }
    throw new Error(`Unexpected fetch: ${url}`);
  }));

  render(<App />);
  await screen.findByText("other.gcode");
  fireEvent.change(screen.getByLabelText(/filter.*tag|tag.*filter/i), { target: { value: "urgent" } });
  fireEvent.click(screen.getByRole("button", { name: /apply filters/i }));

  const active = screen.getByRole("region", { name: /active/i });
  await within(active).findByText("matching.gcode");
  expect(within(active).queryByText("other.gcode")).not.toBeInTheDocument();
});
