import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "../src/app";
import * as jobImportClient from "../src/job-import-api-client";


const apiBaseUrl = "http://localhost:8000/api/v1";
const artifactId = "artifact-calibration-cube";
const job = {
  id: `job-${artifactId}`,
  state: "ready",
  executionData: {
    artifactRef: artifactId,
    material: "PLA",
  },
};

const { loadRuntimeConfig, fetchBackendConfig, fetchBackendHealth, importGcode, createJob, fetchQueue } = vi.hoisted(() => ({
  loadRuntimeConfig: vi.fn(),
  fetchBackendConfig: vi.fn(),
  fetchBackendHealth: vi.fn(),
  importGcode: vi.fn(),
  createJob: vi.fn(),
  fetchQueue: vi.fn(),
}));


vi.mock("../src/runtime-config", () => ({
  loadRuntimeConfig,
}));

vi.mock("../src/backend-health", () => ({
  fetchBackendConfig,
  fetchBackendHealth,
}));

vi.mock("../src/job-import-api-client", () => ({
  importGcode,
  createJob,
  fetchQueue,
}));

const typedClient = vi.mocked(jobImportClient);


afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.resetAllMocks();
});


describe("G-code import client boundary", () => {
  it("imports, creates, and refreshes the active queue through the typed job-import client", async () => {
    loadRuntimeConfig.mockResolvedValue({ apiBaseUrl });
    fetchBackendHealth.mockResolvedValue({ status: "ok" });
    fetchBackendConfig.mockResolvedValue({ appName: "print-job-manager", apiBasePath: "/api/v1" });
    importGcode.mockResolvedValue({
      artifact: { id: artifactId, filename: "calibration-cube.gcode" },
      missingPlanningValues: ["material"],
    });
    createJob.mockResolvedValue(job);
    fetchQueue.mockResolvedValue({ jobs: [job] });
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);

        if (url === `${apiBaseUrl}/import`) {
          return {
            ok: true,
            json: async () => ({
              artifact: { id: artifactId, filename: "calibration-cube.gcode" },
              missingPlanningValues: ["material"],
            }),
          };
        }

        if (url === `${apiBaseUrl}/import/${artifactId}/jobs`) {
          return { ok: true, json: async () => job };
        }

        if (url === `${apiBaseUrl}/queue`) {
          return { ok: true, json: async () => ({ jobs: [job] }) };
        }

        throw new Error(`Unexpected direct fetch: ${url}`);
      }),
    );

    render(<App />);

    const gcode = new File(["G28\nG1 X10 Y10\n"], "calibration-cube.gcode", { type: "text/x.gcode" });
    fireEvent.change(await screen.findByLabelText(/g-code file/i), { target: { files: [gcode] } });

    expect(await screen.findByText(/material.*required|required.*material/i)).toBeInTheDocument();
    expect(importGcode).toHaveBeenCalledWith(apiBaseUrl, gcode);

    fireEvent.change(screen.getByLabelText(/^material$/i), { target: { value: "PLA" } });
    fireEvent.click(screen.getByRole("button", { name: /create job/i }));

    expect(await screen.findByRole("heading", { name: /active queue/i })).toBeInTheDocument();
    expect(createJob).toHaveBeenCalledWith(apiBaseUrl, artifactId, { material: "PLA" });
    expect(fetchQueue).toHaveBeenCalledWith(apiBaseUrl);
    expect(screen.getByText("calibration-cube.gcode")).toBeInTheDocument();
  });

  it("requires a non-material planning value from import review and submits it through the typed client", async () => {
    loadRuntimeConfig.mockResolvedValue({ apiBaseUrl });
    fetchBackendHealth.mockResolvedValue({ status: "ok" });
    fetchBackendConfig.mockResolvedValue({ appName: "print-job-manager", apiBasePath: "/api/v1" });
    typedClient.importGcode.mockResolvedValue({
      artifact: { id: artifactId, filename: "calibration-cube.gcode" },
      missingPlanningValues: ["estimatedDuration"],
    });
    typedClient.createJob.mockResolvedValue(job);
    typedClient.fetchQueue.mockResolvedValue({ jobs: [job] });

    render(<App />);

    fireEvent.change(await screen.findByLabelText(/g-code file/i), {
      target: { files: [new File(["G28\n"], "calibration-cube.gcode", { type: "text/x.gcode" })] },
    });

    const estimatedDuration = await screen.findByLabelText(/estimated duration/i);
    expect(screen.getByRole("button", { name: /create job/i })).toBeDisabled();

    fireEvent.change(estimatedDuration, { target: { value: "60" } });
    expect(screen.getByRole("button", { name: /create job/i })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: /create job/i }));

    expect(typedClient.createJob).toHaveBeenCalledWith(apiBaseUrl, artifactId, { estimatedDuration: "60" });
  });
});
