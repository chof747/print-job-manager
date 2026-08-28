import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "../src/app";


const apiBaseUrl = "http://localhost:8000/api/v1";
const artifactId = "artifact-calibration-cube";
const job = {
  id: `job-${artifactId}`,
  state: "ready",
  executionData: {
    artifactRef: artifactId,
    material: "PLA",
  },
  schedulingData: {
    priority: 0,
  },
};


function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  };
}


afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.resetAllMocks();
});


describe("G-code import", () => {
  it("guides file selection to G-code files", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);

      if (url === "/runtime-config.json") {
        return jsonResponse({ apiBaseUrl });
      }

      if (url === `${apiBaseUrl}/health`) {
        return jsonResponse({ status: "ok" });
      }

      if (url === `${apiBaseUrl}/config`) {
        return jsonResponse({ appName: "print-job-manager", apiBasePath: "/api/v1" });
      }

      throw new Error(`Unexpected fetch: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByLabelText(/g-code file/i)).toHaveAttribute("accept", ".gcode");
  });

  it("shows an upload error when importing the selected G-code fails", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

      if (url === "/runtime-config.json") {
        return jsonResponse({ apiBaseUrl });
      }

      if (url === `${apiBaseUrl}/health`) {
        return jsonResponse({ status: "ok" });
      }

      if (url === `${apiBaseUrl}/config`) {
        return jsonResponse({ appName: "print-job-manager", apiBasePath: "/api/v1" });
      }

      if (url === `${apiBaseUrl}/import` && init?.method === "POST") {
        throw new Error("Upload service unavailable");
      }

      throw new Error(`Unexpected fetch: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.change(await screen.findByLabelText(/g-code file/i), {
      target: { files: [new File(["G28\n"], "calibration-cube.gcode", { type: "text/x.gcode" })] },
    });

    expect(await screen.findByRole("alert")).toHaveTextContent(/upload service unavailable/i);
  });

  it("requires missing material before explicitly creating a ready job in the active queue", async () => {
    let queueJobs: typeof job[] = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

      if (url === "/runtime-config.json") {
        return jsonResponse({ apiBaseUrl });
      }

      if (url === `${apiBaseUrl}/health`) {
        return jsonResponse({ status: "ok" });
      }

      if (url === `${apiBaseUrl}/config`) {
        return jsonResponse({ appName: "print-job-manager", apiBasePath: "/api/v1" });
      }

      if (url === `${apiBaseUrl}/queue`) {
        return jsonResponse({ jobs: queueJobs });
      }

      if (url === `${apiBaseUrl}/import` && init?.method === "POST") {
        expect(init.body).toBeInstanceOf(FormData);
        expect((init.body as FormData).get("file")).toBeInstanceOf(File);

        return jsonResponse({
          artifact: {
            id: artifactId,
            filename: "calibration-cube.gcode",
            mediaType: "text/x.gcode",
          },
          missingPlanningValues: ["material"],
          diagnostics: [],
        }, 201);
      }

      if (url === `${apiBaseUrl}/import/${artifactId}/jobs` && init?.method === "POST") {
        expect(JSON.parse(String(init.body))).toEqual({ material: "PLA" });
        queueJobs = [job];

        return jsonResponse(job, 201);
      }

      throw new Error(`Unexpected fetch: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const gcode = new File(["G28\nG1 X10 Y10\n"], "calibration-cube.gcode", {
      type: "text/x.gcode",
    });
    fireEvent.change(await screen.findByLabelText(/g-code file/i), {
      target: { files: [gcode] },
    });

    expect(await screen.findByText(/material.*required|required.*material/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create job/i })).toBeDisabled();

    fireEvent.change(screen.getByLabelText(/^material$/i), { target: { value: "PLA" } });
    expect(screen.getByRole("button", { name: /create job/i })).toBeEnabled();

    fireEvent.click(screen.getByRole("button", { name: /create job/i }));

    expect(await screen.findByRole("heading", { name: /active queue/i })).toBeInTheDocument();
    expect(await screen.findByText("calibration-cube.gcode")).toBeInTheDocument();
    expect(screen.getByText(/ready/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(`${apiBaseUrl}/queue`);
    });
  });

  it("rejects whitespace-only material and shows create failures", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

      if (url === "/runtime-config.json") {
        return jsonResponse({ apiBaseUrl });
      }

      if (url === `${apiBaseUrl}/health`) {
        return jsonResponse({ status: "ok" });
      }

      if (url === `${apiBaseUrl}/config`) {
        return jsonResponse({ appName: "print-job-manager", apiBasePath: "/api/v1" });
      }

      if (url === `${apiBaseUrl}/import` && init?.method === "POST") {
        return jsonResponse({
          artifact: {
            id: artifactId,
            filename: "calibration-cube.gcode",
            mediaType: "text/x.gcode",
          },
          missingPlanningValues: ["material"],
          diagnostics: [],
        }, 201);
      }

      if (url === `${apiBaseUrl}/import/${artifactId}/jobs` && init?.method === "POST") {
        return jsonResponse({ detail: "Unable to create job" }, 500);
      }

      throw new Error(`Unexpected fetch: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.change(await screen.findByLabelText(/g-code file/i), {
      target: { files: [new File(["G28\n"], "calibration-cube.gcode", { type: "text/x.gcode" })] },
    });

    const materialInput = await screen.findByLabelText(/^material$/i);
    fireEvent.change(materialInput, { target: { value: "   " } });
    expect(screen.getByRole("button", { name: /create job/i })).toBeDisabled();

    fireEvent.change(materialInput, { target: { value: "PLA" } });
    fireEvent.click(screen.getByRole("button", { name: /create job/i }));

    expect(await screen.findByText(/unable to create job/i)).toBeVisible();
  });

  it("shows missing planning values from a create validation failure as text", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

      if (url === "/runtime-config.json") {
        return jsonResponse({ apiBaseUrl });
      }

      if (url === `${apiBaseUrl}/health`) {
        return jsonResponse({ status: "ok" });
      }

      if (url === `${apiBaseUrl}/config`) {
        return jsonResponse({ appName: "print-job-manager", apiBasePath: "/api/v1" });
      }

      if (url === `${apiBaseUrl}/import` && init?.method === "POST") {
        return jsonResponse({
          artifact: {
            id: artifactId,
            filename: "calibration-cube.gcode",
            mediaType: "text/x.gcode",
          },
          missingPlanningValues: ["material"],
          diagnostics: [],
        }, 201);
      }

      if (url === `${apiBaseUrl}/import/${artifactId}/jobs` && init?.method === "POST") {
        return jsonResponse({ detail: { missingPlanningValues: ["material"] } }, 422);
      }

      throw new Error(`Unexpected fetch: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.change(await screen.findByLabelText(/g-code file/i), {
      target: { files: [new File(["G28\n"], "calibration-cube.gcode", { type: "text/x.gcode" })] },
    });
    fireEvent.change(await screen.findByLabelText(/^material$/i), { target: { value: "PLA" } });
    fireEvent.click(screen.getByRole("button", { name: /create job/i }));

    expect(await screen.findByText(/missing planning values: material/i)).toBeVisible();
  });

  it("reports queue refresh failure without claiming that job creation failed", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

      if (url === "/runtime-config.json") {
        return jsonResponse({ apiBaseUrl });
      }

      if (url === `${apiBaseUrl}/health`) {
        return jsonResponse({ status: "ok" });
      }

      if (url === `${apiBaseUrl}/config`) {
        return jsonResponse({ appName: "print-job-manager", apiBasePath: "/api/v1" });
      }

      if (url === `${apiBaseUrl}/import` && init?.method === "POST") {
        return jsonResponse({
          artifact: { id: artifactId, filename: "calibration-cube.gcode" },
          missingPlanningValues: ["material"],
        }, 201);
      }

      if (url === `${apiBaseUrl}/import/${artifactId}/jobs` && init?.method === "POST") {
        return jsonResponse(job, 201);
      }

      if (url === `${apiBaseUrl}/queue`) {
        return jsonResponse({}, 500);
      }

      throw new Error(`Unexpected fetch: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.change(await screen.findByLabelText(/g-code file/i), {
      target: { files: [new File(["G28\n"], "calibration-cube.gcode", { type: "text/x.gcode" })] },
    });
    fireEvent.change(await screen.findByLabelText(/^material$/i), { target: { value: "PLA" } });
    fireEvent.click(screen.getByRole("button", { name: /create job/i }));

    expect(await screen.findByText(/job was created, but the active queue could not be refreshed/i)).toBeVisible();
  });
});
