import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "../src/app";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("informs the user when a scheduling edit is stale and preserves the draft", async () => {
  const apiBaseUrl = "http://localhost:8000/api/v1";
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/runtime-config.json") return { ok: true, json: async () => ({ apiBaseUrl }) };
    if (url === `${apiBaseUrl}/health`) return { ok: true, json: async () => ({ status: "ok" }) };
    if (url === `${apiBaseUrl}/config`) return { ok: true, json: async () => ({ appName: "print-job-manager" }) };
    if (url === `${apiBaseUrl}/cockpit`) return { ok: true, headers: { get: (): string => "application/json" }, json: async () => ({ activeJobs: [{
      id: "job-1", state: "ready", version: 0,
      executionData: { artifactRef: "sha256:job", artifactFilename: "job.gcode" },
      schedulingData: { priority: 0 },
    }], failures: [], recentHistory: [] }) };
    if (url === `${apiBaseUrl}/queue`) return { ok: true, json: async () => ({ jobs: [{
      id: "job-1", state: "ready", version: 0,
      executionData: { artifactRef: "sha256:job", artifactFilename: "job.gcode" },
      schedulingData: { priority: 0 },
    }] }) };
    if (url === `${apiBaseUrl}/jobs/job-1/scheduling`) return {
      ok: false, status: 409,
      headers: { get: () => "application/json" },
      json: async () => ({ detail: { code: "version_conflict", currentVersion: 1 } }),
    };
    throw new Error(`Unexpected API request: ${url}`);
  }));

  render(<App />);
  await screen.findByText("job.gcode");
  fireEvent.click(screen.getByRole("button", { name: /edit scheduling/i }));
  fireEvent.change(screen.getByLabelText(/^priority$/i), { target: { value: "10" } });
  fireEvent.click(screen.getByRole("button", { name: /save scheduling/i }));

  expect(await screen.findByRole("alert")).toHaveTextContent(/stale|conflict|changed/i);
  expect(screen.getByLabelText(/^priority$/i)).toHaveValue(10);
});

it("does not submit a stale draft with a refreshed job version", async () => {
  const apiBaseUrl = "http://localhost:8000/api/v1";
  const job = {
    id: "job-1", state: "ready", version: 0,
    executionData: { artifactRef: "sha256:job", artifactFilename: "job.gcode" },
    schedulingData: { priority: 0 },
  };
  let queueRequests = 0;
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/runtime-config.json") return { ok: true, json: async () => ({ apiBaseUrl }) };
    if (url === `${apiBaseUrl}/health`) return { ok: true, json: async () => ({ status: "ok" }) };
    if (url === `${apiBaseUrl}/config`) return { ok: true, json: async () => ({ appName: "print-job-manager" }) };
    if (url === `${apiBaseUrl}/queue`) {
      queueRequests += 1;
      return { ok: true, json: async () => ({ jobs: [queueRequests === 1 ? job : {
        ...job, version: 1, schedulingData: { priority: 20 },
      }] }) };
    }
    if (url === `${apiBaseUrl}/import`) return { ok: true, json: async () => ({
      artifact: { id: "new-artifact", filename: "new.gcode" }, missingPlanningValues: [],
    }) };
    if (url === `${apiBaseUrl}/import/new-artifact/jobs`) return { ok: true, json: async () => job };
    if (url === `${apiBaseUrl}/jobs/job-1/scheduling` && init?.method === "PATCH") return {
      ok: false, status: 409, json: async () => ({ detail: { code: "version_conflict", currentVersion: 1 } }),
    };
    throw new Error(`Unexpected API request: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  await screen.findByText("job.gcode");
  fireEvent.click(screen.getByRole("button", { name: /edit scheduling/i }));
  fireEvent.change(screen.getByLabelText(/^priority$/i), { target: { value: "10" } });
  fireEvent.change(screen.getByLabelText(/g-code file/i), {
    target: { files: [new File(["G28"], "new.gcode", { type: "text/x.gcode" })] },
  });
  fireEvent.click(await screen.findByRole("button", { name: /create job/i }));
  await screen.findByRole("status", { name: /job created/i });
  fireEvent.click(screen.getByRole("button", { name: /save scheduling/i }));

  await waitFor(() => {
    const request = fetchMock.mock.calls.find(([url, init]) =>
      String(url) === `${apiBaseUrl}/jobs/job-1/scheduling` && init?.method === "PATCH",
    );
    if (request) {
      expect(JSON.parse(String(request[1]?.body)).expectedVersion).toBe(0);
    } else {
      expect(screen.getByRole("alert")).toHaveTextContent(/stale|conflict|changed/i);
    }
  });
});
