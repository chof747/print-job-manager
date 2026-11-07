import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "../src/app";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("explains how to correct a partial build volume requirement", async () => {
  const base = "http://localhost:8000/api/v1";
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
    throw new Error(`Unexpected fetch: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  fireEvent.change(await screen.findByLabelText(/g-code file/i), {
    target: { files: [new File(["G28"], "part.gcode", { type: "text/x.gcode" })] },
  });
  fireEvent.change(await screen.findByLabelText(/minimum build volume x/i), { target: { value: "200" } });
  fireEvent.click(screen.getByRole("button", { name: /create job/i }));

  expect(await screen.findByRole("alert")).toHaveTextContent(/build volume.*(all|x.*y.*z|three)|(?:all|x.*y.*z|three).*build volume/i);
  expect(screen.queryByText(/this job has all required planning values/i)).not.toBeInTheDocument();
  expect(fetchMock.mock.calls.some(([url]) => String(url) === `${base}/import/artifact-1/jobs`)).toBe(false);
});
