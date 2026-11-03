import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "../src/app";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("shows active jobs, failures and recent history in the cockpit after creating a job", async () => {
  const base = "http://localhost:8000/api/v1";
  const job = (id: string, state: string, filename: string) => ({
    id, state, version: 0,
    executionData: { artifactRef: id, artifactFilename: filename, material: "PLA" },
    schedulingData: { priority: 0 },
  });
  const active = job("new-job", "ready", "new.gcode");
  const failure = job("failed-job", "failed", "failed.gcode");
  const completed = job("completed-job", "completed", "completed.gcode");
  const json = (body: unknown, status = 200) => ({
    ok: status >= 200 && status < 300, status, headers: { get: () => "application/json" }, json: async () => body,
  });
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/runtime-config.json") return json({ apiBaseUrl: base });
    if (url === `${base}/health`) return json({ status: "ok" });
    if (url === `${base}/config`) return json({ appName: "print-job-manager" });
    if (url === `${base}/queue`) return json({ jobs: [active] });
    if (url === `${base}/cockpit`) return json({
      activeJobs: [active], failures: [failure], recentHistory: [failure, completed],
    });
    if (url === `${base}/import` && init?.method === "POST") {
      return json({ artifact: { id: "new", filename: "new.gcode" }, missingPlanningValues: [], diagnostics: [] }, 201);
    }
    if (url === `${base}/import/new/jobs` && init?.method === "POST") return json(active, 201);
    throw new Error(`Unexpected fetch: ${url}`);
  }));

  render(<App />);
  fireEvent.change(await screen.findByLabelText(/g-code file/i), {
    target: { files: [new File(["G28"], "new.gcode", { type: "text/x.gcode" })] },
  });
  fireEvent.click(await screen.findByRole("button", { name: /create job/i }));
  await screen.findByRole("status", { name: /job created/i });

  expect(within(screen.getByRole("region", { name: /active/i })).getByText("new.gcode")).toBeVisible();
  expect(within(await screen.findByRole("region", { name: /failures/i })).getByText("failed.gcode")).toBeVisible();
  expect(within(screen.getByRole("region", { name: /recent history/i })).getByText(/completed\.gcode/i)).toBeVisible();
});

it("shows an active job's planning context in its cockpit summary", async () => {
  const base = "http://localhost:8000/api/v1";
  const active = {
    id: "job-1", state: "ready", version: 1,
    executionData: { artifactRef: "artifact-1", artifactFilename: "bracket.gcode", material: "PETG" },
    schedulingData: {
      priority: 25, dueDate: "2026-11-07",
      printerAssignment: { mode: "required", printerId: "printer-mk4" },
    },
  };
  const json = (body: unknown) => ({ ok: true, status: 200, headers: { get: () => "application/json" }, json: async () => body });
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/runtime-config.json") return json({ apiBaseUrl: base });
    if (url === `${base}/health`) return json({ status: "ok" });
    if (url === `${base}/config`) return json({ appName: "print-job-manager" });
    if (url === `${base}/queue`) return json({ jobs: [active] });
    if (url === `${base}/cockpit`) return json({ activeJobs: [active], failures: [], recentHistory: [] });
    throw new Error(`Unexpected fetch: ${url}`);
  }));

  render(<App />);
  await screen.findByText("bracket.gcode");
  const summary = screen.getByRole("region", { name: /active/i });

  expect(summary).toHaveTextContent(/ready/i);
  expect(summary).toHaveTextContent(/priority\s*:?\s*25/i);
  expect(summary).toHaveTextContent("2026-11-07");
  expect(summary).toHaveTextContent("PETG");
  expect(summary).toHaveTextContent(/required/i);
  expect(summary).toHaveTextContent("printer-mk4");
});

it("shows lifecycle outcomes alongside recent history jobs", async () => {
  const base = "http://localhost:8000/api/v1";
  const history = ["completed", "failed", "cancelled", "archived"].map((state) => ({
    id: `job-${state}`, state, version: 0,
    executionData: { artifactRef: state, artifactFilename: `${state}.gcode`, material: "PLA" },
    schedulingData: { priority: 0 },
  }));
  const json = (body: unknown) => ({ ok: true, status: 200, headers: { get: () => "application/json" }, json: async () => body });
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/runtime-config.json") return json({ apiBaseUrl: base });
    if (url === `${base}/health`) return json({ status: "ok" });
    if (url === `${base}/config`) return json({ appName: "print-job-manager" });
    if (url === `${base}/queue`) return json({ jobs: [] });
    if (url === `${base}/cockpit`) return json({ activeJobs: [], failures: [history[1]], recentHistory: history });
    throw new Error(`Unexpected fetch: ${url}`);
  }));

  render(<App />);
  const region = await screen.findByRole("region", { name: /recent history/i });
  for (const state of ["completed", "failed", "cancelled", "archived"]) {
    await within(region).findByText(new RegExp(`${state}\\.gcode`, "i"));
    expect(region.textContent?.replaceAll(/(?:completed|failed|cancelled|archived)\.gcode/gi, "")).toMatch(
      new RegExp(state, "i"),
    );
  }
});

it("opens a historical job's details from its cockpit summary", async () => {
  const base = "http://localhost:8000/api/v1";
  const completed = {
    id: "job-history-1", state: "completed", version: 0,
    executionData: { artifactRef: "artifact-1", artifactFilename: "finished.gcode", material: "PETG" },
    schedulingData: { priority: 12 },
  };
  const json = (body: unknown) => ({ ok: true, status: 200, headers: { get: () => "application/json" }, json: async () => body });
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/runtime-config.json") return json({ apiBaseUrl: base });
    if (url === `${base}/health`) return json({ status: "ok" });
    if (url === `${base}/config`) return json({ appName: "print-job-manager" });
    if (url === `${base}/queue`) return json({ jobs: [] });
    if (url === `${base}/cockpit`) return json({ activeJobs: [], failures: [], recentHistory: [completed] });
    if (url === `${base}/jobs/job-history-1`) return json(completed);
    throw new Error(`Unexpected fetch: ${url}`);
  }));

  render(<App />);
  const history = await screen.findByRole("region", { name: /recent history/i });
  await within(history).findByText(/finished\.gcode/i);
  fireEvent.click(within(history).getByRole("button", { name: /details/i }));

  const details = await screen.findByRole("region", { name: /job details/i });
  expect(details).toHaveTextContent("finished.gcode");
  expect(details).toHaveTextContent("PETG");
  expect(details).toHaveTextContent(/completed/i);
});

it("presents the active cockpit before guided import after creating a job", async () => {
  const base = "http://localhost:8000/api/v1";
  const job = {
    id: "new-job", state: "ready", version: 0,
    executionData: { artifactRef: "new", artifactFilename: "new.gcode", material: "PLA" },
    schedulingData: { priority: 0 },
  };
  const json = (body: unknown, status = 200) => ({
    ok: status >= 200 && status < 300, status, headers: { get: () => "application/json" }, json: async () => body,
  });
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/runtime-config.json") return json({ apiBaseUrl: base });
    if (url === `${base}/health`) return json({ status: "ok" });
    if (url === `${base}/config`) return json({ appName: "print-job-manager" });
    if (url === `${base}/queue`) return json({ jobs: [job] });
    if (url === `${base}/cockpit`) return json({ activeJobs: [job], failures: [], recentHistory: [] });
    if (url === `${base}/import` && init?.method === "POST") {
      return json({ artifact: { id: "new", filename: "new.gcode" }, missingPlanningValues: [], diagnostics: [] }, 201);
    }
    if (url === `${base}/import/new/jobs` && init?.method === "POST") return json(job, 201);
    throw new Error(`Unexpected fetch: ${url}`);
  }));

  render(<App />);
  fireEvent.change(await screen.findByLabelText(/g-code file/i), {
    target: { files: [new File(["G28"], "new.gcode", { type: "text/x.gcode" })] },
  });
  fireEvent.click(await screen.findByRole("button", { name: /create job/i }));
  await screen.findByRole("status", { name: /job created/i });

  const active = screen.getByRole("region", { name: /active/i });
  const importRegion = screen.getByRole("region", { name: /guided import/i });
  expect(active.compareDocumentPosition(importRegion) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
});

it("opens an active job's details from the cockpit", async () => {
  const base = "http://localhost:8000/api/v1";
  const active = {
    id: "job-active", state: "ready", version: 0,
    executionData: { artifactRef: "artifact-1", artifactFilename: "active.gcode", material: "PLA" },
    schedulingData: { priority: 10 },
  };
  const json = (body: unknown) => ({ ok: true, status: 200, headers: { get: () => "application/json" }, json: async () => body });
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/runtime-config.json") return json({ apiBaseUrl: base });
    if (url === `${base}/health`) return json({ status: "ok" });
    if (url === `${base}/config`) return json({ appName: "print-job-manager" });
    if (url === `${base}/queue`) return json({ jobs: [active] });
    if (url === `${base}/cockpit`) return json({ activeJobs: [active], failures: [], recentHistory: [] });
    if (url === `${base}/jobs/job-active`) return json(active);
    throw new Error(`Unexpected fetch: ${url}`);
  }));

  render(<App />);
  const queue = await screen.findByRole("region", { name: /active/i });
  await within(queue).findByText("active.gcode");
  fireEvent.click(within(queue).getByRole("button", { name: /details/i }));

  const details = await screen.findByRole("region", { name: /job details/i });
  expect(details).toHaveTextContent("active.gcode");
  expect(details).toHaveTextContent("PLA");
  expect(details).toHaveTextContent(/ready/i);
});

it("renders active jobs from the cockpit projection", async () => {
  const base = "http://localhost:8000/api/v1";
  const active = {
    id: "cockpit-job", state: "ready", version: 0,
    executionData: { artifactRef: "artifact-1", artifactFilename: "cockpit.gcode", material: "PLA" },
    schedulingData: { priority: 5 },
  };
  const json = (body: unknown) => ({ ok: true, status: 200, headers: { get: () => "application/json" }, json: async () => body });
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/runtime-config.json") return json({ apiBaseUrl: base });
    if (url === `${base}/health`) return json({ status: "ok" });
    if (url === `${base}/config`) return json({ appName: "print-job-manager" });
    if (url === `${base}/queue`) return json({ jobs: [] });
    if (url === `${base}/cockpit`) return json({ activeJobs: [active], failures: [], recentHistory: [] });
    throw new Error(`Unexpected fetch: ${url}`);
  }));

  render(<App />);
  const queue = await screen.findByRole("region", { name: /active/i });
  expect(await within(queue).findByText("cockpit.gcode")).toBeVisible();
});

it("keeps a newly created job visible while the cockpit refresh is pending", async () => {
  const base = "http://localhost:8000/api/v1";
  const job = {
    id: "new-job", state: "ready", version: 0,
    executionData: { artifactRef: "new", artifactFilename: "new.gcode", material: "PLA" },
    schedulingData: { priority: 0 },
  };
  const json = (body: unknown, status = 200) => ({
    ok: status >= 200 && status < 300, status, headers: { get: () => "application/json" }, json: async () => body,
  });
  let created = false;
  let finishRefresh!: (response: ReturnType<typeof json>) => void;
  const pending = new Promise<ReturnType<typeof json>>((resolve) => { finishRefresh = resolve; });
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/runtime-config.json") return json({ apiBaseUrl: base });
    if (url === `${base}/health`) return json({ status: "ok" });
    if (url === `${base}/config`) return json({ appName: "print-job-manager" });
    if (url === `${base}/queue`) return json({ jobs: created ? [job] : [] });
    if (url === `${base}/cockpit`) return created ? pending : json({ activeJobs: [], failures: [], recentHistory: [] });
    if (url === `${base}/import` && init?.method === "POST") {
      return json({ artifact: { id: "new", filename: "new.gcode" }, missingPlanningValues: [], diagnostics: [] }, 201);
    }
    if (url === `${base}/import/new/jobs` && init?.method === "POST") {
      created = true;
      return json(job, 201);
    }
    throw new Error(`Unexpected fetch: ${url}`);
  }));

  try {
    render(<App />);
    await screen.findByText(/no active jobs yet/i);
    fireEvent.change(await screen.findByLabelText(/g-code file/i), {
      target: { files: [new File(["G28"], "new.gcode", { type: "text/x.gcode" })] },
    });
    fireEvent.click(await screen.findByRole("button", { name: /create job/i }));
    await screen.findByRole("status", { name: /job created/i });

    expect(within(screen.getByRole("region", { name: /active/i })).getByText("new.gcode")).toBeVisible();
  } finally {
    finishRefresh(json({ activeJobs: [job], failures: [], recentHistory: [] }));
  }
});

it("reports a cockpit loading failure instead of silently showing empty history", async () => {
  const base = "http://localhost:8000/api/v1";
  const json = (body: unknown, status = 200) => ({
    ok: status >= 200 && status < 300, status, headers: { get: () => "application/json" }, json: async () => body,
  });
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/runtime-config.json") return json({ apiBaseUrl: base });
    if (url === `${base}/health`) return json({ status: "ok" });
    if (url === `${base}/config`) return json({ appName: "print-job-manager" });
    if (url === `${base}/queue`) return json({ jobs: [] });
    if (url === `${base}/cockpit`) return json({ detail: "unavailable" }, 503);
    throw new Error(`Unexpected fetch: ${url}`);
  }));

  render(<App />);

  expect(await screen.findByRole("alert")).toHaveTextContent(/cockpit/i);
});

it("does not show a newly created job that does not match the active material filter", async () => {
  const base = "http://localhost:8000/api/v1";
  const job = {
    id: "petg-job", state: "ready", version: 0,
    executionData: { artifactRef: "new", artifactFilename: "petg.gcode", material: "PETG" },
    schedulingData: { priority: 0 },
  };
  const json = (body: unknown, status = 200) => ({
    ok: status >= 200 && status < 300, status, headers: { get: () => "application/json" }, json: async () => body,
  });
  let created = false;
  let finishRefresh!: (response: ReturnType<typeof json>) => void;
  const pending = new Promise<ReturnType<typeof json>>((resolve) => { finishRefresh = resolve; });
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/runtime-config.json") return json({ apiBaseUrl: base });
    if (url === `${base}/health`) return json({ status: "ok" });
    if (url === `${base}/config`) return json({ appName: "print-job-manager" });
    if (url === `${base}/queue`) return json({ jobs: created ? [job] : [] });
    if (url.startsWith(`${base}/cockpit`)) return created ? pending : json({ activeJobs: [], failures: [], recentHistory: [] });
    if (url === `${base}/import` && init?.method === "POST") {
      return json({ artifact: { id: "new", filename: "petg.gcode" }, extractedMetadata: { material: "PETG" }, missingPlanningValues: [], diagnostics: [] }, 201);
    }
    if (url === `${base}/import/new/jobs` && init?.method === "POST") {
      created = true;
      return json(job, 201);
    }
    throw new Error(`Unexpected fetch: ${url}`);
  }));

  try {
    render(<App />);
    await screen.findByText(/no active jobs yet/i);
    fireEvent.change(screen.getByLabelText(/filter.*material|material.*filter/i), { target: { value: "PLA" } });
    fireEvent.click(screen.getByRole("button", { name: /apply filters/i }));
    await screen.findByText(/no active jobs yet/i);
    fireEvent.change(await screen.findByLabelText(/g-code file/i), {
      target: { files: [new File(["G28"], "petg.gcode", { type: "text/x.gcode" })] },
    });
    fireEvent.click(await screen.findByRole("button", { name: /create job/i }));
    await screen.findByRole("status", { name: /job created/i });

    expect(within(screen.getByRole("region", { name: /active/i })).queryByText("petg.gcode")).not.toBeInTheDocument();
  } finally {
    finishRefresh(json({ activeJobs: [], failures: [], recentHistory: [] }));
  }
});

it("lets an operator filter cockpit jobs by material", async () => {
  const base = "http://localhost:8000/api/v1";
  const job = (material: string) => ({
    id: `job-${material}`, state: "ready", version: 0,
    executionData: { artifactRef: material, artifactFilename: `${material}.gcode`, material },
    schedulingData: { priority: 0 },
  });
  const pla = job("PLA");
  const petg = job("PETG");
  const json = (body: unknown) => ({ ok: true, status: 200, headers: { get: () => "application/json" }, json: async () => body });
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/runtime-config.json") return json({ apiBaseUrl: base });
    if (url === `${base}/health`) return json({ status: "ok" });
    if (url === `${base}/config`) return json({ appName: "print-job-manager" });
    if (url === `${base}/queue`) return json({ jobs: [pla, petg] });
    if (url.startsWith(`${base}/cockpit`)) {
      const material = new URL(url).searchParams.get("material");
      return json({ activeJobs: material === "PLA" ? [pla] : [pla, petg], failures: [], recentHistory: [] });
    }
    throw new Error(`Unexpected fetch: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  await screen.findByText("PETG.gcode");
  fireEvent.change(screen.getByLabelText(/filter.*material|material.*filter/i), { target: { value: "PLA" } });
  fireEvent.click(screen.getByRole("button", { name: /apply filters/i }));

  const active = screen.getByRole("region", { name: /active/i });
  await within(active).findByText("PLA.gcode");
  expect(within(active).queryByText("PETG.gcode")).not.toBeInTheDocument();
  expect(fetchMock.mock.calls.some(([url]) =>
    String(url).startsWith(`${base}/cockpit?`) && new URL(String(url)).searchParams.get("material") === "PLA",
  )).toBe(true);
});

it("lets an operator combine print, scheduling and parser-quality filters", async () => {
  const base = "http://localhost:8000/api/v1";
  const job = (id: string) => ({
    id, state: "ready", version: 0,
    executionData: { artifactRef: id, artifactFilename: `${id}.gcode`, material: "PLA" },
    schedulingData: { priority: 10 },
  });
  const match = job("matching");
  const other = job("other");
  const json = (body: unknown) => ({ ok: true, status: 200, headers: { get: () => "application/json" }, json: async () => body });
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/runtime-config.json") return json({ apiBaseUrl: base });
    if (url === `${base}/health`) return json({ status: "ok" });
    if (url === `${base}/config`) return json({ appName: "print-job-manager" });
    if (url === `${base}/queue`) return json({ jobs: [match, other] });
    if (url.startsWith(`${base}/cockpit`)) {
      const params = new URL(url).searchParams;
      const filtered = params.get("minDurationSeconds") === "1800" &&
        params.get("minPriority") === "5" && params.get("diagnosticCode") === "malformed_metadata";
      return json({ activeJobs: filtered ? [match] : [match, other], failures: [], recentHistory: [] });
    }
    throw new Error(`Unexpected fetch: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  await screen.findByText("other.gcode");
  fireEvent.change(screen.getByLabelText(/minimum duration/i), { target: { value: "1800" } });
  fireEvent.change(screen.getByLabelText(/minimum priority/i), { target: { value: "5" } });
  fireEvent.change(screen.getByLabelText(/diagnostic code/i), { target: { value: "malformed_metadata" } });
  fireEvent.click(screen.getByRole("button", { name: /apply filters/i }));

  const active = screen.getByRole("region", { name: /active/i });
  await within(active).findByText("matching.gcode");
  expect(within(active).queryByText("other.gcode")).not.toBeInTheDocument();
  expect(fetchMock.mock.calls.some(([url]) => {
    if (!String(url).startsWith(`${base}/cockpit?`)) return false;
    const params = new URL(String(url)).searchParams;
    return params.get("minDurationSeconds") === "1800" && params.get("minPriority") === "5" &&
      params.get("diagnosticCode") === "malformed_metadata";
  })).toBe(true);
});

it("opens details for a failure even when it is absent from recent history", async () => {
  const base = "http://localhost:8000/api/v1";
  const failed = {
    id: "job-failed", state: "failed", version: 0,
    executionData: { artifactRef: "artifact-1", artifactFilename: "failed.gcode", material: "PETG" },
    schedulingData: { priority: 0 },
  };
  const json = (body: unknown) => ({ ok: true, status: 200, headers: { get: () => "application/json" }, json: async () => body });
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/runtime-config.json") return json({ apiBaseUrl: base });
    if (url === `${base}/health`) return json({ status: "ok" });
    if (url === `${base}/config`) return json({ appName: "print-job-manager" });
    if (url === `${base}/queue`) return json({ jobs: [] });
    if (url === `${base}/cockpit`) return json({ activeJobs: [], failures: [failed], recentHistory: [] });
    if (url === `${base}/jobs/job-failed`) return json(failed);
    throw new Error(`Unexpected fetch: ${url}`);
  }));

  render(<App />);
  const failures = await screen.findByRole("region", { name: /failures/i });
  await within(failures).findByText("failed.gcode");
  fireEvent.click(within(failures).getByRole("button", { name: /details/i }));

  const details = await screen.findByRole("region", { name: /job details/i });
  expect(details).toHaveTextContent("failed.gcode");
  expect(details).toHaveTextContent("PETG");
  expect(details).toHaveTextContent(/failed/i);
});
