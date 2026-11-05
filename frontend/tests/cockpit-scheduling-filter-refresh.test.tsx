import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "../src/app";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("removes a job from the priority slice after its scheduling edit no longer matches", async () => {
  const base = "http://localhost:8000/api/v1";
  let job = {
    id: "job-1", state: "ready", version: 0,
    executionData: { artifactRef: "artifact-1", artifactFilename: "bracket.gcode", material: "PLA" },
    schedulingData: { priority: 10 },
  };
  const json = (body: unknown) => ({ ok: true, status: 200, headers: { get: () => "application/json" }, json: async () => body });
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/runtime-config.json") return json({ apiBaseUrl: base });
    if (url === `${base}/health`) return json({ status: "ok" });
    if (url === `${base}/config`) return json({ appName: "print-job-manager" });
    if (url === `${base}/queue`) return json({ jobs: [job] });
    if (url.startsWith(`${base}/cockpit`)) {
      const minimum = new URL(url).searchParams.get("minPriority");
      return json({ activeJobs: !minimum || job.schedulingData.priority >= Number(minimum) ? [job] : [], failures: [], recentHistory: [] });
    }
    if (url === `${base}/jobs/job-1/scheduling` && init?.method === "PATCH") {
      job = { ...job, version: 1, schedulingData: { priority: 0 } };
      return json(job);
    }
    throw new Error(`Unexpected fetch: ${url}`);
  }));

  render(<App />);
  await screen.findByText("bracket.gcode");
  if (screen.queryByRole("button", { name: "Open filter rail" })) fireEvent.click(screen.getByRole("button", { name: "Open filter rail" }));
  fireEvent.change(screen.getByLabelText(/minimum priority/i), { target: { value: "5" } });
  fireEvent.click(screen.getByRole("button", { name: /apply filters/i }));
  const active = screen.getByRole("region", { name: /active/i });
  await within(active).findByText("bracket.gcode");
  fireEvent.click(within(active).getByRole("button", { name: /edit scheduling/i }));
  fireEvent.change(screen.getByLabelText(/^priority$/i), { target: { value: "0" } });
  fireEvent.click(screen.getByRole("button", { name: /save scheduling/i }));

  await waitFor(() => expect(job.version).toBe(1));
  await waitFor(() => expect(within(active).queryByText("bracket.gcode")).not.toBeInTheDocument());
});
