import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "../src/app";

const { fetchBackendConfig, fetchBackendHealth, fetchQueue, loadRuntimeConfig, updateJobScheduling } = vi.hoisted(() => ({
  fetchBackendConfig: vi.fn(),
  fetchBackendHealth: vi.fn(),
  fetchQueue: vi.fn(),
  loadRuntimeConfig: vi.fn(),
  updateJobScheduling: vi.fn(),
}));

vi.mock("../src/runtime-config", () => ({ loadRuntimeConfig }));
vi.mock("../src/backend-health", () => ({ fetchBackendConfig, fetchBackendHealth }));
vi.mock("../src/job-import-api-client", () => ({
  importGcode: vi.fn(), createJob: vi.fn(), fetchQueue, updateJobScheduling,
}));

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

it("does not silently save a blank priority as zero", async () => {
  loadRuntimeConfig.mockResolvedValue({ apiBaseUrl: "http://localhost:8000/api/v1" });
  fetchBackendHealth.mockResolvedValue({ status: "ok" });
  fetchBackendConfig.mockResolvedValue({ appName: "print-job-manager" });
  fetchQueue.mockResolvedValue({ jobs: [{
    id: "job-1", state: "ready", version: 0,
    executionData: { artifactRef: "sha256:job", artifactFilename: "job.gcode" },
    schedulingData: { priority: 10 },
  }] });

  render(<App />);
  await screen.findByText("job.gcode");
  fireEvent.click(screen.getByRole("button", { name: /edit scheduling/i }));
  fireEvent.change(screen.getByLabelText(/^priority$/i), { target: { value: "" } });
  fireEvent.click(screen.getByRole("button", { name: /save scheduling/i }));

  expect(updateJobScheduling).not.toHaveBeenCalled();
  expect(await screen.findByRole("alert")).toHaveTextContent(/priority/i);
});
