import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "../src/app";


const apiBaseUrl = "http://localhost:8000/api/v1";
const job = {
  id: "job-calibration-cube",
  state: "ready",
  version: 0,
  executionData: {
    artifactRef: "sha256:calibration-cube",
    artifactFilename: "calibration-cube.gcode",
  },
  schedulingData: { priority: 0 },
};

const { fetchBackendConfig, fetchBackendHealth, fetchQueue, loadRuntimeConfig, updateJobScheduling } = vi.hoisted(() => ({
  fetchBackendConfig: vi.fn(),
  fetchBackendHealth: vi.fn(),
  fetchQueue: vi.fn(),
  loadRuntimeConfig: vi.fn(),
  updateJobScheduling: vi.fn(),
}));


vi.mock("../src/runtime-config", () => ({
  loadRuntimeConfig,
}));

vi.mock("../src/backend-health", () => ({
  fetchBackendConfig,
  fetchBackendHealth,
}));

vi.mock("../src/job-import-api-client", () => ({
  importGcode: vi.fn(),
  createJob: vi.fn(),
  fetchQueue,
  updateJobScheduling,
}));


afterEach(() => {
  cleanup();
  vi.resetAllMocks();
  vi.unstubAllGlobals();
});


it("edits a queued job priority with its current version and renders the updated value", async () => {
  loadRuntimeConfig.mockResolvedValue({ apiBaseUrl });
  fetchBackendHealth.mockResolvedValue({ status: "ok" });
  fetchBackendConfig.mockResolvedValue({ appName: "print-job-manager", apiBasePath: "/api/v1" });
  fetchQueue.mockResolvedValue({ jobs: [job] });
  updateJobScheduling.mockResolvedValue({
    ...job,
    version: 1,
    schedulingData: { priority: 10 },
  });

  render(<App />);

  await screen.findByText("calibration-cube.gcode");
  fireEvent.click(screen.getByRole("button", { name: /edit scheduling/i }));
  fireEvent.change(screen.getByLabelText(/^priority$/i), { target: { value: "10" } });
  fireEvent.click(screen.getByRole("button", { name: /save scheduling/i }));

  await waitFor(() => expect(updateJobScheduling).toHaveBeenCalledWith(apiBaseUrl, job.id, {
    priority: 10,
    expectedVersion: 0,
  }));
  expect(await screen.findByDisplayValue("10")).toBeInTheDocument();
});

it("edits a queued job due date with its current version", async () => {
  loadRuntimeConfig.mockResolvedValue({ apiBaseUrl });
  fetchBackendHealth.mockResolvedValue({ status: "ok" });
  fetchBackendConfig.mockResolvedValue({ appName: "print-job-manager", apiBasePath: "/api/v1" });
  fetchQueue.mockResolvedValue({ jobs: [job] });
  updateJobScheduling.mockResolvedValue({
    ...job,
    version: 1,
    schedulingData: { priority: 0, dueDate: "2026-11-07" },
  });

  render(<App />);

  await screen.findByText("calibration-cube.gcode");
  fireEvent.click(screen.getByRole("button", { name: /edit scheduling/i }));
  fireEvent.change(screen.getByLabelText(/due date/i), { target: { value: "2026-11-07" } });
  fireEvent.click(screen.getByRole("button", { name: /save scheduling/i }));

  await waitFor(() => expect(updateJobScheduling).toHaveBeenCalledWith(apiBaseUrl, job.id, {
    dueDate: "2026-11-07",
    expectedVersion: 0,
  }));
  expect(await screen.findByDisplayValue("2026-11-07")).toBeInTheDocument();
});

it("edits queued job notes with its current version", async () => {
  loadRuntimeConfig.mockResolvedValue({ apiBaseUrl });
  fetchBackendHealth.mockResolvedValue({ status: "ok" });
  fetchBackendConfig.mockResolvedValue({ appName: "print-job-manager", apiBasePath: "/api/v1" });
  fetchQueue.mockResolvedValue({ jobs: [job] });
  updateJobScheduling.mockResolvedValue({
    ...job,
    version: 1,
    schedulingData: { priority: 0, notes: "Deliver before the trade show." },
  });

  render(<App />);

  await screen.findByText("calibration-cube.gcode");
  fireEvent.click(screen.getByRole("button", { name: /edit scheduling/i }));
  fireEvent.change(screen.getByLabelText(/notes/i), { target: { value: "Deliver before the trade show." } });
  fireEvent.click(screen.getByRole("button", { name: /save scheduling/i }));

  await waitFor(() => expect(updateJobScheduling).toHaveBeenCalledWith(apiBaseUrl, job.id, expect.objectContaining({
    notes: "Deliver before the trade show.",
    expectedVersion: 0,
  })));
  expect(await screen.findByDisplayValue("Deliver before the trade show.")).toBeInTheDocument();
});

it("edits queued job tags with its current version", async () => {
  loadRuntimeConfig.mockResolvedValue({ apiBaseUrl });
  fetchBackendHealth.mockResolvedValue({ status: "ok" });
  fetchBackendConfig.mockResolvedValue({ appName: "print-job-manager", apiBasePath: "/api/v1" });
  fetchQueue.mockResolvedValue({ jobs: [job] });
  updateJobScheduling.mockResolvedValue({
    ...job,
    version: 1,
    schedulingData: { priority: 0, tags: ["customer-order", "urgent"] },
  });

  render(<App />);

  await screen.findByText("calibration-cube.gcode");
  fireEvent.click(screen.getByRole("button", { name: /edit scheduling/i }));
  fireEvent.change(screen.getByLabelText(/tags/i), { target: { value: "customer-order, urgent" } });
  fireEvent.click(screen.getByRole("button", { name: /save scheduling/i }));

  await waitFor(() => expect(updateJobScheduling).toHaveBeenCalledWith(apiBaseUrl, job.id, expect.objectContaining({
    tags: ["customer-order", "urgent"],
    expectedVersion: 0,
  })));
  expect(await screen.findByDisplayValue(/customer-order.*urgent/i)).toBeInTheDocument();
});

it("preserves a comma-containing tag when editing priority", async () => {
  const taggedJob = { ...job, schedulingData: { priority: 0, tags: ["customer, urgent"] } };
  loadRuntimeConfig.mockResolvedValue({ apiBaseUrl });
  fetchBackendHealth.mockResolvedValue({ status: "ok" });
  fetchBackendConfig.mockResolvedValue({ appName: "print-job-manager", apiBasePath: "/api/v1" });
  fetchQueue.mockResolvedValue({ jobs: [taggedJob] });
  updateJobScheduling.mockResolvedValue({
    ...taggedJob, version: 1, schedulingData: { ...taggedJob.schedulingData, priority: 10 },
  });

  render(<App />);
  await screen.findByText("calibration-cube.gcode");
  fireEvent.click(screen.getByRole("button", { name: /edit scheduling/i }));
  fireEvent.change(screen.getByLabelText(/^priority$/i), { target: { value: "10" } });
  fireEvent.click(screen.getByRole("button", { name: /save scheduling/i }));

  await waitFor(() => expect(updateJobScheduling).toHaveBeenCalledWith(apiBaseUrl, job.id, {
    priority: 10,
    expectedVersion: 0,
  }));
  expect(await screen.findByDisplayValue('"customer, urgent"')).toBeInTheDocument();
});

it("preserves a comma-containing tag when adding another tag", async () => {
  const taggedJob = { ...job, schedulingData: { priority: 0, tags: ["customer, west"] } };
  loadRuntimeConfig.mockResolvedValue({ apiBaseUrl });
  fetchBackendHealth.mockResolvedValue({ status: "ok" });
  fetchBackendConfig.mockResolvedValue({ appName: "print-job-manager", apiBasePath: "/api/v1" });
  fetchQueue.mockResolvedValue({ jobs: [taggedJob] });
  updateJobScheduling.mockResolvedValue({
    ...taggedJob, version: 1,
    schedulingData: { priority: 0, tags: ["customer, west", "urgent"] },
  });

  render(<App />);
  await screen.findByText("calibration-cube.gcode");
  fireEvent.click(screen.getByRole("button", { name: /edit scheduling/i }));
  fireEvent.change(screen.getByLabelText(/tags/i), {
    target: { value: '"customer, west", urgent' },
  });
  fireEvent.click(screen.getByRole("button", { name: /save scheduling/i }));

  await waitFor(() => expect(updateJobScheduling).toHaveBeenCalledWith(apiBaseUrl, job.id, {
    tags: ["customer, west", "urgent"],
    expectedVersion: 0,
  }));
});

it("edits a queued job preferred printer assignment with its current version", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ["printer-mk4"] }));
  loadRuntimeConfig.mockResolvedValue({ apiBaseUrl });
  fetchBackendHealth.mockResolvedValue({ status: "ok" });
  fetchBackendConfig.mockResolvedValue({ appName: "print-job-manager", apiBasePath: "/api/v1" });
  fetchQueue.mockResolvedValue({ jobs: [job] });
  updateJobScheduling.mockResolvedValue({
    ...job,
    version: 1,
    schedulingData: { priority: 0, printerAssignment: { mode: "preferred", printerId: "printer-mk4" } },
  });

  render(<App />);

  await screen.findByText("calibration-cube.gcode");
  fireEvent.click(screen.getByRole("button", { name: /edit scheduling/i }));
  fireEvent.change(screen.getByLabelText(/assignment mode/i), { target: { value: "preferred" } });
  await screen.findByRole("option", { name: "printer-mk4" });
  fireEvent.change(screen.getByLabelText(/printer id/i), { target: { value: "printer-mk4" } });
  fireEvent.click(screen.getByRole("button", { name: /save scheduling/i }));

  await waitFor(() => expect(updateJobScheduling).toHaveBeenCalledWith(apiBaseUrl, job.id, expect.objectContaining({
    printerAssignment: { mode: "preferred", printerId: "printer-mk4" },
    expectedVersion: 0,
  })));
  expect(await screen.findByDisplayValue("printer-mk4")).toBeInTheDocument();
});

it("edits a queued job required printer assignment with its current version", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ["printer-mk4"] }));
  loadRuntimeConfig.mockResolvedValue({ apiBaseUrl });
  fetchBackendHealth.mockResolvedValue({ status: "ok" });
  fetchBackendConfig.mockResolvedValue({ appName: "print-job-manager", apiBasePath: "/api/v1" });
  fetchQueue.mockResolvedValue({ jobs: [job] });
  updateJobScheduling.mockResolvedValue({
    ...job,
    version: 1,
    schedulingData: { priority: 0, printerAssignment: { mode: "required", printerId: "printer-mk4" } },
  });

  render(<App />);

  await screen.findByText("calibration-cube.gcode");
  fireEvent.click(screen.getByRole("button", { name: /edit scheduling/i }));
  fireEvent.change(screen.getByLabelText(/assignment mode/i), { target: { value: "required" } });
  await screen.findByRole("option", { name: "printer-mk4" });
  fireEvent.change(screen.getByLabelText(/printer id/i), { target: { value: "printer-mk4" } });
  fireEvent.click(screen.getByRole("button", { name: /save scheduling/i }));

  await waitFor(() => expect(updateJobScheduling).toHaveBeenCalledWith(apiBaseUrl, job.id, expect.objectContaining({
    printerAssignment: { mode: "required", printerId: "printer-mk4" },
    expectedVersion: 0,
  })));
  expect(await screen.findByDisplayValue("printer-mk4")).toBeInTheDocument();
});
