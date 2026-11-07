import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "../src/app";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("explains satisfied requirements for an eligible job and printer", async () => {
  const base = "http://localhost:8000/api/v1";
  const job = {
    id: "job-1", state: "ready", version: 0,
    executionData: { artifactRef: "artifact-1", artifactFilename: "part.gcode", material: "PLA", requirements: { enclosure: true } },
    schedulingData: { priority: 0 },
  };
  const json = (body: unknown) => ({ ok: true, status: 200, headers: { get: () => "application/json" }, json: async () => body });
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/runtime-config.json") return json({ apiBaseUrl: base });
    if (url === `${base}/health`) return json({ status: "ok" });
    if (url === `${base}/config`) return json({ appName: "print-job-manager" });
    if (url === `${base}/queue`) return json({ jobs: [job] });
    if (url === `${base}/cockpit`) return json({ activeJobs: [job], failures: [], recentHistory: [] });
    if (url === `${base}/jobs/job-1`) return json(job);
    if (url === `${base}/jobs/job-1/eligibility` && init?.method === "POST") {
      return json({ eligible: true, blocked: false, failures: [], satisfied: [{ code: "enclosure_satisfied" }] });
    }
    throw new Error(`Unexpected fetch: ${url}`);
  }));

  render(<App />);
  const active = await screen.findByRole("region", { name: /active/i });
  await within(active).findByText("part.gcode");
  fireEvent.click(within(active).getByRole("button", { name: /details/i }));
  const details = await screen.findByRole("region", { name: /job details/i });
  fireEvent.change(within(details).getByLabelText(/printer id/i), { target: { value: "printer-1" } });
  fireEvent.click(within(details).getByRole("button", { name: /check eligibility/i }));

  expect(await within(details).findByText(/eligible/i)).toBeVisible();
  expect(await within(details).findByText(/enclosure.*satisfied|enclosure.*met/i)).toBeVisible();
});
