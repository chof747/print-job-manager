import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "../src/app";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("declares material and hardened nozzle as hard requirements during import", async () => {
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
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/runtime-config.json") return json({ apiBaseUrl: base });
    if (url === `${base}/health`) return json({ status: "ok" });
    if (url === `${base}/config`) return json({ appName: "print-job-manager" });
    if (url === `${base}/queue`) return json({ jobs: [] });
    if (url === `${base}/cockpit`) return json({ activeJobs: [], failures: [], recentHistory: [] });
    if (url === `${base}/import` && init?.method === "POST") {
      return json({ artifact: { id: "artifact-1", filename: "part.gcode" }, extractedMetadata: { material: "PLA" }, missingPlanningValues: [], diagnostics: [] }, 201);
    }
    if (url === `${base}/import/artifact-1/jobs` && init?.method === "POST") return json(job, 201);
    throw new Error(`Unexpected fetch: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  fireEvent.change(await screen.findByLabelText(/g-code file/i), {
    target: { files: [new File(["G28"], "part.gcode", { type: "text/x.gcode" })] },
  });
  fireEvent.click(await screen.findByRole("checkbox", { name: /require.*hardened nozzle|hardened nozzle.*required/i }));
  fireEvent.change(screen.getByLabelText(/material color/i), { target: { value: "black" } });
  fireEvent.change(screen.getByLabelText(/material amount/i), { target: { value: "100" } });
  fireEvent.click(screen.getByRole("button", { name: /create job/i }));

  await waitFor(() => {
    const call = fetchMock.mock.calls.find(([url]) => String(url) === `${base}/import/artifact-1/jobs`);
    expect(call).toBeDefined();
    const payload = JSON.parse(String(call![1]?.body));
    expect(payload.requirements).toMatchObject({ hardenedNozzle: true, material: { color: "black", amountGrams: 100 } });
    expect(payload.schedulingData?.requirements).toBeUndefined();
  });
});
