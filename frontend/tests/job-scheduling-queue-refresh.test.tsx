import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "../src/app";

const api = vi.hoisted(() => ({
  fetchBackendConfig: vi.fn(), fetchBackendHealth: vi.fn(), fetchQueue: vi.fn(),
  loadRuntimeConfig: vi.fn(), updateJobScheduling: vi.fn(), importGcode: vi.fn(),
  createJob: vi.fn(),
}));

vi.mock("../src/runtime-config", () => ({ loadRuntimeConfig: api.loadRuntimeConfig }));
vi.mock("../src/backend-health", () => ({
  fetchBackendConfig: api.fetchBackendConfig, fetchBackendHealth: api.fetchBackendHealth,
}));
vi.mock("../src/job-import-api-client", () => api);

afterEach(() => { cleanup(); vi.resetAllMocks(); });

it("keeps a newly created job visible when the initial queue response arrives late", async () => {
  const job = {
    id: "job-new", state: "ready", version: 0,
    executionData: { artifactRef: "sha256:new", artifactFilename: "new.gcode" },
    schedulingData: { priority: 0 },
  };
  let finishInitialQueue!: (queue: { jobs: (typeof job)[] }) => void;
  const initialQueue = new Promise<{ jobs: (typeof job)[] }>((resolve) => { finishInitialQueue = resolve; });
  api.loadRuntimeConfig.mockResolvedValue({ apiBaseUrl: "http://localhost:8000/api/v1" });
  api.fetchBackendHealth.mockResolvedValue({ status: "ok" });
  api.fetchBackendConfig.mockResolvedValue({ appName: "print-job-manager" });
  api.fetchQueue.mockReturnValueOnce(initialQueue).mockResolvedValueOnce({ jobs: [job] });
  api.importGcode.mockResolvedValue({ artifact: { id: "new", filename: "new.gcode" }, missingPlanningValues: [] });
  api.createJob.mockResolvedValue(job);

  render(<App />);
  await waitFor(() => expect(api.fetchQueue).toHaveBeenCalledTimes(1));
  fireEvent.change(screen.getByLabelText(/g-code file/i), {
    target: { files: [new File(["G28"], "new.gcode", { type: "text/x.gcode" })] },
  });
  fireEvent.click(await screen.findByRole("button", { name: /create job/i }));
  await screen.findByRole("status", { name: /job created/i });
  const queue = screen.getByRole("region", { name: /active queue/i });
  expect(queue).toHaveTextContent("new.gcode");

  await act(async () => {
    finishInitialQueue({ jobs: [] });
    await initialQueue;
    await new Promise((resolve) => setTimeout(resolve, 50));
  });

  expect(queue).toHaveTextContent("new.gcode");
});

it("keeps a newer queue priority when an older save response arrives later", async () => {
  const job = {
    id: "job-1", state: "ready", version: 0,
    executionData: { artifactRef: "sha256:job", artifactFilename: "job.gcode" },
    schedulingData: { priority: 0 },
  };
  let finishSave!: (savedJob: typeof job) => void;
  const pendingSave = new Promise<typeof job>((resolve) => { finishSave = resolve; });
  api.loadRuntimeConfig.mockResolvedValue({ apiBaseUrl: "http://localhost:8000/api/v1" });
  api.fetchBackendHealth.mockResolvedValue({ status: "ok" });
  api.fetchBackendConfig.mockResolvedValue({ appName: "print-job-manager" });
  api.fetchQueue.mockResolvedValueOnce({ jobs: [job] }).mockResolvedValueOnce({
    jobs: [{ ...job, version: 2, schedulingData: { priority: 20 } }],
  });
  api.updateJobScheduling.mockReturnValue(pendingSave);
  api.importGcode.mockResolvedValue({ artifact: { id: "new", filename: "new.gcode" }, missingPlanningValues: [] });
  api.createJob.mockResolvedValue(job);

  render(<App />);
  await screen.findByText("job.gcode");
  fireEvent.click(screen.getByRole("button", { name: /edit scheduling/i }));
  fireEvent.change(screen.getByLabelText(/^priority$/i), { target: { value: "10" } });
  fireEvent.click(screen.getByRole("button", { name: /save scheduling/i }));
  await waitFor(() => expect(api.updateJobScheduling).toHaveBeenCalledWith(
    "http://localhost:8000/api/v1", "job-1", { priority: 10, expectedVersion: 0 },
  ));
  fireEvent.change(screen.getByLabelText(/g-code file/i), {
    target: { files: [new File(["G28"], "new.gcode", { type: "text/x.gcode" })] },
  });
  fireEvent.click(await screen.findByRole("button", { name: /create job/i }));
  await screen.findByRole("status", { name: /job created/i });
  const queue = screen.getByRole("region", { name: /active queue/i });
  expect(queue).toHaveTextContent(/priority\s*:?\s*20/i);

  await act(async () => {
    finishSave({ ...job, version: 1, schedulingData: { priority: 10 } });
    await pendingSave;
  });

  expect(queue).toHaveTextContent(/priority\s*:?\s*20/i);
});

it("shows a successfully edited priority in the queue outside the editor", async () => {
  const job = {
    id: "job-1", state: "ready", version: 0,
    executionData: { artifactRef: "sha256:job", artifactFilename: "job.gcode" },
    schedulingData: { priority: 0 },
  };
  const otherJob = { ...job, id: "job-2", executionData: { artifactRef: "sha256:other", artifactFilename: "other.gcode" } };
  api.loadRuntimeConfig.mockResolvedValue({ apiBaseUrl: "http://localhost:8000/api/v1" });
  api.fetchBackendHealth.mockResolvedValue({ status: "ok" });
  api.fetchBackendConfig.mockResolvedValue({ appName: "print-job-manager" });
  api.fetchQueue.mockResolvedValue({ jobs: [job, otherJob] });
  api.updateJobScheduling.mockResolvedValue({ ...job, version: 1, schedulingData: { priority: 10 } });

  render(<App />);
  await screen.findByText("job.gcode");
  fireEvent.click(screen.getAllByRole("button", { name: /edit scheduling/i })[0]);
  fireEvent.change(screen.getByLabelText(/^priority$/i), { target: { value: "10" } });
  fireEvent.click(screen.getByRole("button", { name: /save scheduling/i }));
  await waitFor(() => expect(api.updateJobScheduling).toHaveBeenCalledWith(
    "http://localhost:8000/api/v1", "job-1", { priority: 10, expectedVersion: 0 },
  ));
  fireEvent.click(screen.getByRole("button", { name: /edit scheduling/i }));

  const queue = screen.getByRole("region", { name: /active queue/i });
  expect(queue).toHaveTextContent(/priority\s*:?\s*10/i);
});

it("keeps a successful scheduling edit when an older queue refresh completes later", async () => {
  const job = {
    id: "job-1", state: "ready", version: 0,
    executionData: { artifactRef: "sha256:job", artifactFilename: "job.gcode" },
    schedulingData: { priority: 0 },
  };
  const otherJob = { ...job, id: "job-2", executionData: { artifactRef: "sha256:other", artifactFilename: "other.gcode" } };
  let finishRefresh!: (queue: { jobs: typeof job[] }) => void;
  const pendingRefresh = new Promise<{ jobs: typeof job[] }>((resolve) => { finishRefresh = resolve; });
  api.loadRuntimeConfig.mockResolvedValue({ apiBaseUrl: "http://localhost:8000/api/v1" });
  api.fetchBackendHealth.mockResolvedValue({ status: "ok" });
  api.fetchBackendConfig.mockResolvedValue({ appName: "print-job-manager" });
  api.fetchQueue.mockResolvedValueOnce({ jobs: [job, otherJob] }).mockReturnValueOnce(pendingRefresh);
  api.importGcode.mockResolvedValue({ artifact: { id: "new", filename: "new.gcode" }, missingPlanningValues: [] });
  api.createJob.mockResolvedValue(job);
  api.updateJobScheduling.mockResolvedValue({ ...job, version: 1, schedulingData: { priority: 10 } });

  render(<App />);
  await screen.findByText("job.gcode");
  fireEvent.change(screen.getByLabelText(/g-code file/i), {
    target: { files: [new File(["G28"], "new.gcode", { type: "text/x.gcode" })] },
  });
  fireEvent.click(await screen.findByRole("button", { name: /create job/i }));
  await waitFor(() => expect(api.fetchQueue).toHaveBeenCalledTimes(2));
  fireEvent.click(screen.getAllByRole("button", { name: /edit scheduling/i })[0]);
  fireEvent.change(screen.getByLabelText(/^priority$/i), { target: { value: "10" } });
  fireEvent.click(screen.getByRole("button", { name: /save scheduling/i }));
  await waitFor(() => expect(api.updateJobScheduling).toHaveBeenCalled());
  await act(async () => { finishRefresh({ jobs: [job, otherJob] }); await pendingRefresh; });

  // Switch jobs and reopen the first to read the queue projection rather than the draft.
  fireEvent.click(screen.getByRole("button", { name: /edit scheduling/i }));
  fireEvent.click(screen.getByRole("button", { name: /edit scheduling/i }));
  expect(screen.getByLabelText(/^priority$/i)).toHaveValue(10);
});

it("keeps the second job's draft attached to that job when the first save finishes", async () => {
  const jobA = {
    id: "job-a", state: "ready", version: 0,
    executionData: { artifactRef: "sha256:a", artifactFilename: "a.gcode" },
    schedulingData: { priority: 0 },
  };
  const jobB = {
    id: "job-b", state: "ready", version: 0,
    executionData: { artifactRef: "sha256:b", artifactFilename: "b.gcode" },
    schedulingData: { priority: 0 },
  };
  let finishSave!: (job: typeof jobA) => void;
  const pendingSave = new Promise<typeof jobA>((resolve) => { finishSave = resolve; });
  api.loadRuntimeConfig.mockResolvedValue({ apiBaseUrl: "http://localhost:8000/api/v1" });
  api.fetchBackendHealth.mockResolvedValue({ status: "ok" });
  api.fetchBackendConfig.mockResolvedValue({ appName: "print-job-manager" });
  api.fetchQueue.mockResolvedValue({ jobs: [jobA, jobB] });
  api.updateJobScheduling.mockReturnValueOnce(pendingSave).mockResolvedValueOnce({
    ...jobB, version: 1, schedulingData: { priority: 20 },
  });

  render(<App />);
  await screen.findByText("a.gcode");
  fireEvent.click(screen.getAllByRole("button", { name: /edit scheduling/i })[0]);
  fireEvent.change(screen.getByLabelText(/^priority$/i), { target: { value: "10" } });
  fireEvent.click(screen.getByRole("button", { name: /save scheduling/i }));
  fireEvent.click(screen.getByRole("button", { name: /edit scheduling/i }));
  fireEvent.change(screen.getByLabelText(/^priority$/i), { target: { value: "20" } });
  await act(async () => {
    finishSave({ ...jobA, version: 1, schedulingData: { priority: 10 } });
    await pendingSave;
  });
  fireEvent.click(screen.getByRole("button", { name: /save scheduling/i }));

  await waitFor(() => expect(api.updateJobScheduling).toHaveBeenLastCalledWith(
    "http://localhost:8000/api/v1", "job-b", { priority: 20, expectedVersion: 0 },
  ));
});

it("does not silently revert a save when the same job is reopened before it completes", async () => {
  const jobA = {
    id: "job-a", state: "ready", version: 0,
    executionData: { artifactRef: "sha256:a", artifactFilename: "a.gcode" },
    schedulingData: { priority: 0 },
  };
  const jobB = {
    id: "job-b", state: "ready", version: 0,
    executionData: { artifactRef: "sha256:b", artifactFilename: "b.gcode" },
    schedulingData: { priority: 0 },
  };
  let finishSave!: (job: typeof jobA) => void;
  const pendingSave = new Promise<typeof jobA>((resolve) => { finishSave = resolve; });
  api.loadRuntimeConfig.mockResolvedValue({ apiBaseUrl: "http://localhost:8000/api/v1" });
  api.fetchBackendHealth.mockResolvedValue({ status: "ok" });
  api.fetchBackendConfig.mockResolvedValue({ appName: "print-job-manager" });
  api.fetchQueue.mockResolvedValue({ jobs: [jobA, jobB] });
  api.updateJobScheduling.mockReturnValueOnce(pendingSave).mockResolvedValue({
    ...jobA, version: 2, schedulingData: { priority: 0 },
  });

  render(<App />);
  await screen.findByText("a.gcode");
  fireEvent.click(screen.getAllByRole("button", { name: /edit scheduling/i })[0]);
  fireEvent.change(screen.getByLabelText(/^priority$/i), { target: { value: "10" } });
  fireEvent.click(screen.getByRole("button", { name: /save scheduling/i }));
  fireEvent.click(screen.getByRole("button", { name: /edit scheduling/i }));
  fireEvent.click(screen.getByRole("button", { name: /edit scheduling/i }));
  await act(async () => {
    finishSave({ ...jobA, version: 1, schedulingData: { priority: 10 } });
    await pendingSave;
  });
  fireEvent.click(screen.getByRole("button", { name: /save scheduling/i }));

  expect(api.updateJobScheduling).not.toHaveBeenCalledWith(
    "http://localhost:8000/api/v1", "job-a", { priority: 0, expectedVersion: 1 },
  );
});
