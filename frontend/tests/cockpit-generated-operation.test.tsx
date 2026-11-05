import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { App } from "../src/app";
import { SchedulingClient } from "../src/generated/scheduling/SchedulingClient";
import { DefaultService } from "../src/generated/scheduling/services/DefaultService";
import { FetchHttpRequest } from "../src/generated/scheduling/core/FetchHttpRequest";

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it("exposes the cockpit projection through the generated API client", async () => {
  const projection = { activeJobs: [], failures: [], recentHistory: [] };
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(projection), {
    status: 200, headers: { "Content-Type": "application/json" },
  }));
  vi.stubGlobal("fetch", fetchMock);
  const client = new SchedulingClient({ BASE: "http://localhost:8000/api/v1" });
  const operation: unknown = Reflect.get(client.default, "cockpitApiV1CockpitGet");

  expect(operation).toBeTypeOf("function");
  if (typeof operation !== "function") return;
  const result = await operation.call(client.default, { material: "PLA" });

  expect(result).toEqual(projection);
  const request = fetchMock.mock.calls[0][0] as RequestInfo | URL;
  const url = new URL(request instanceof Request ? request.url : String(request));
  expect(url.pathname).toBe("/api/v1/cockpit");
  expect(url.searchParams.get("material")).toBe("PLA");
});

it("uses the generated cockpit operation when an operator applies planning filters", async () => {
  const base = "http://localhost:8000/api/v1";
  const operation = vi.spyOn(DefaultService.prototype, "cockpitApiV1CockpitGet");
  const json = (body: unknown) => new Response(JSON.stringify(body), {
    status: 200, headers: { "Content-Type": "application/json" },
  });
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = input instanceof Request ? input.url : String(input);
    if (url === "/runtime-config.json") return json({ apiBaseUrl: base });
    if (url === `${base}/health`) return json({ status: "ok" });
    if (url === `${base}/config`) return json({ appName: "print-job-manager" });
    if (url === `${base}/queue`) return json({ jobs: [] });
    if (url.startsWith(`${base}/cockpit`)) return json({ activeJobs: [], failures: [], recentHistory: [] });
    throw new Error(`Unexpected fetch: ${url}`);
  }));

  render(<App />);
  await screen.findByText(/no active jobs yet/i);
  if (screen.queryByRole("button", { name: "Open filter rail" })) fireEvent.click(screen.getByRole("button", { name: "Open filter rail" }));
  fireEvent.change(screen.getByLabelText(/filter by material/i), { target: { value: "PLA" } });
  if (screen.queryByRole("button", { name: "Open filter rail" })) fireEvent.click(screen.getByRole("button", { name: "Open filter rail" }));
  fireEvent.change(screen.getByLabelText(/minimum priority/i), { target: { value: "5" } });
  fireEvent.click(screen.getByRole("button", { name: /apply filters/i }));

  await waitFor(() => expect(operation).toHaveBeenCalledWith(expect.objectContaining({ material: "PLA", minPriority: 5 })));
});

it("uses the generated client when an operator opens job details", async () => {
  const base = "http://localhost:8000/api/v1";
  const job = {
    id: "job-1", state: "ready", version: 0,
    executionData: { artifactRef: "artifact-1", artifactFilename: "bracket.gcode", material: "PLA" },
    schedulingData: { priority: 0 },
  };
  const request = vi.spyOn(FetchHttpRequest.prototype, "request");
  const json = (body: unknown) => new Response(JSON.stringify(body), {
    status: 200, headers: { "Content-Type": "application/json" },
  });
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = input instanceof Request ? input.url : String(input);
    if (url === "/runtime-config.json") return json({ apiBaseUrl: base });
    if (url === `${base}/health`) return json({ status: "ok" });
    if (url === `${base}/config`) return json({ appName: "print-job-manager" });
    if (url === `${base}/queue`) return json({ jobs: [job] });
    if (url.startsWith(`${base}/cockpit`)) return json({ activeJobs: [job], failures: [], recentHistory: [] });
    if (url === `${base}/jobs/job-1`) return json(job);
    throw new Error(`Unexpected fetch: ${url}`);
  }));

  render(<App />);
  await screen.findByText("bracket.gcode");
  fireEvent.click(screen.getByRole("button", { name: /details/i }));
  expect(await screen.findByRole("region", { name: /job details/i })).toHaveTextContent("bracket.gcode");
  expect(request).toHaveBeenCalledWith(expect.objectContaining({
    method: "GET", url: "/jobs/{job_id}", path: { job_id: "job-1" },
  }));
});
