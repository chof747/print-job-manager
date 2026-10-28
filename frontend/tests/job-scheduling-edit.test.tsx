import { cleanup, fireEvent, render, screen } from "@testing-library/react";
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

  expect(updateJobScheduling).toHaveBeenCalledWith(apiBaseUrl, job.id, {
    priority: 10,
    expectedVersion: 0,
  });
  expect(await screen.findByDisplayValue("10")).toBeInTheDocument();
});
