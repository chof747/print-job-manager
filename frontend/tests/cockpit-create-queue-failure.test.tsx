import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "../src/app";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("shows a successfully created job in the cockpit even if queue refresh fails", async () => {
  const base = "http://localhost:8000/api/v1";
  const job = {
    id: "new-job", state: "ready", version: 0,
    executionData: { artifactRef: "new", artifactFilename: "new.gcode", material: "PLA" },
    schedulingData: { priority: 0 },
  };
  let created = false;
  const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
    status, headers: { "Content-Type": "application/json" },
  });
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = input instanceof Request ? input.url : String(input);
    if (url === "/runtime-config.json") return json({ apiBaseUrl: base });
    if (url === `${base}/health`) return json({ status: "ok" });
    if (url === `${base}/config`) return json({ appName: "print-job-manager" });
    if (url === `${base}/queue`) return created ? json({ detail: "unavailable" }, 503) : json({ jobs: [] });
    if (url.startsWith(`${base}/cockpit`)) return json({ activeJobs: created ? [job] : [], failures: [], recentHistory: [] });
    if (url === `${base}/import` && init?.method === "POST") {
      return json({ artifact: { id: "new", filename: "new.gcode" }, missingPlanningValues: [], diagnostics: [] }, 201);
    }
    if (url === `${base}/import/new/jobs` && init?.method === "POST") {
      created = true;
      return json(job, 201);
    }
    throw new Error(`Unexpected fetch: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  await waitFor(() => expect(fetchMock.mock.calls.some(([input]) => String(input).startsWith(`${base}/cockpit`))).toBe(true));
  fireEvent.change(await screen.findByLabelText(/g-code file/i), {
    target: { files: [new File(["G28"], "new.gcode", { type: "text/x.gcode" })] },
  });
  fireEvent.click(await screen.findByRole("button", { name: /create job/i }));
  await screen.findByText(/job was created.*queue could not be refreshed/i);

  expect(await within(screen.getByRole("region", { name: /active/i })).findByText("new.gcode")).toBeVisible();
});
