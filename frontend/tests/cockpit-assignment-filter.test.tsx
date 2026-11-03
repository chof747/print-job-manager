import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "../src/app";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("lets an operator show only jobs without a printer assignment", async () => {
  const base = "http://localhost:8000/api/v1";
  const unassigned = {
    id: "unassigned", state: "ready", version: 0,
    executionData: { artifactRef: "a", artifactFilename: "unassigned.gcode", material: "PLA" },
    schedulingData: { priority: 0 },
  };
  const assigned = {
    ...unassigned, id: "assigned",
    executionData: { ...unassigned.executionData, artifactFilename: "assigned.gcode" },
    schedulingData: { priority: 0, printerAssignment: { mode: "required", printerId: "printer-1" } },
  };
  const json = (body: unknown) => ({ ok: true, status: 200, headers: { get: () => "application/json" }, json: async () => body });
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/runtime-config.json") return json({ apiBaseUrl: base });
    if (url === `${base}/health`) return json({ status: "ok" });
    if (url === `${base}/config`) return json({ appName: "print-job-manager" });
    if (url === `${base}/queue`) return json({ jobs: [unassigned, assigned] });
    if (url.startsWith(`${base}/cockpit`)) {
      const filtered = new URL(url).searchParams.get("assignmentMode") === "unassigned";
      return json({ activeJobs: filtered ? [unassigned] : [unassigned, assigned], failures: [], recentHistory: [] });
    }
    throw new Error(`Unexpected fetch: ${url}`);
  }));

  render(<App />);
  await screen.findByText("assigned.gcode");
  const filter = screen.getByLabelText(/filter.*assignment|assignment.*filter/i);
  fireEvent.change(filter, { target: { value: "unassigned" } });
  fireEvent.click(screen.getByRole("button", { name: /apply filters/i }));

  const active = screen.getByRole("region", { name: /active/i });
  await within(active).findByText("unassigned.gcode");
  await waitFor(() => expect(within(active).queryByText("assigned.gcode")).not.toBeInTheDocument());
});

it("lets an operator slice the cockpit by printer assignment mode", async () => {
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
      const filtered = new URL(url).searchParams.get("assignmentMode") === "required";
      return json({ activeJobs: filtered ? [matching] : [matching, other], failures: [], recentHistory: [] });
    }
    throw new Error(`Unexpected fetch: ${url}`);
  }));

  render(<App />);
  await screen.findByText("other.gcode");
  fireEvent.change(screen.getByLabelText(/filter.*assignment|assignment.*filter/i), { target: { value: "required" } });
  fireEvent.click(screen.getByRole("button", { name: /apply filters/i }));

  const active = screen.getByRole("region", { name: /active/i });
  await within(active).findByText("matching.gcode");
  expect(within(active).queryByText("other.gcode")).not.toBeInTheDocument();
});
