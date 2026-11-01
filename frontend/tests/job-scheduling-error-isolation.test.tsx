import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "../src/app";

const api = vi.hoisted(() => ({
  fetchBackendConfig: vi.fn(), fetchBackendHealth: vi.fn(), fetchQueue: vi.fn(),
  loadRuntimeConfig: vi.fn(), updateJobScheduling: vi.fn(), importGcode: vi.fn(), createJob: vi.fn(),
}));

vi.mock("../src/runtime-config", () => ({ loadRuntimeConfig: api.loadRuntimeConfig }));
vi.mock("../src/backend-health", () => ({
  fetchBackendConfig: api.fetchBackendConfig, fetchBackendHealth: api.fetchBackendHealth,
}));
vi.mock("../src/job-import-api-client", () => api);

afterEach(() => { cleanup(); vi.resetAllMocks(); });

it("does not show a previous job's failed save on another job's edit form", async () => {
  const job = {
    id: "job-a", state: "ready", version: 0,
    executionData: { artifactRef: "sha256:a", artifactFilename: "a.gcode" },
    schedulingData: { priority: 0 },
  };
  const otherJob = {
    ...job, id: "job-b", executionData: { artifactRef: "sha256:b", artifactFilename: "b.gcode" },
  };
  let failSave!: (error: Error) => void;
  const pendingSave = new Promise<never>((_, reject) => { failSave = reject; });
  api.loadRuntimeConfig.mockResolvedValue({ apiBaseUrl: "http://localhost:8000/api/v1" });
  api.fetchBackendHealth.mockResolvedValue({ status: "ok" });
  api.fetchBackendConfig.mockResolvedValue({ appName: "print-job-manager" });
  api.fetchQueue.mockResolvedValue({ jobs: [job, otherJob] });
  api.updateJobScheduling.mockReturnValue(pendingSave);

  render(<App />);
  await screen.findByText("a.gcode");
  fireEvent.click(screen.getAllByRole("button", { name: /edit scheduling/i })[0]);
  fireEvent.change(screen.getByLabelText(/^priority$/i), { target: { value: "10" } });
  fireEvent.click(screen.getByRole("button", { name: /save scheduling/i }));
  fireEvent.click(screen.getByRole("button", { name: /edit scheduling/i }));
  await act(async () => { failSave(new Error("Job A is stale")); await pendingSave.catch(() => {}); });

  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});
