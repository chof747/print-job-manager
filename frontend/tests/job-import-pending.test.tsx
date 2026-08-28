import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "../src/app";


const apiBaseUrl = "http://localhost:8000/api/v1";
const artifactId = "artifact-calibration-cube";


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


describe("G-code import pending state", () => {
  it("shows upload status and prevents another selection or submission while an upload is pending", async () => {
    let importCount = 0;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

      if (url === "/runtime-config.json") {
        return Promise.resolve(jsonResponse({ apiBaseUrl }));
      }

      if (url === `${apiBaseUrl}/health`) {
        return Promise.resolve(jsonResponse({ status: "ok" }));
      }

      if (url === `${apiBaseUrl}/config`) {
        return Promise.resolve(jsonResponse({ appName: "print-job-manager", apiBasePath: "/api/v1" }));
      }

      if (url === `${apiBaseUrl}/import` && init?.method === "POST") {
        importCount += 1;
        if (importCount === 1) {
          return Promise.resolve(jsonResponse({
            artifact: { id: artifactId, filename: "calibration-cube.gcode" },
            missingPlanningValues: ["material"],
          }, 201));
        }

        return new Promise<ReturnType<typeof jsonResponse>>(() => {});
      }

      throw new Error(`Unexpected fetch: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const fileInput = await screen.findByLabelText(/g-code file/i);
    fireEvent.change(fileInput, {
      target: { files: [new File(["G28\n"], "calibration-cube.gcode", { type: "text/x.gcode" })] },
    });
    fireEvent.change(await screen.findByLabelText(/^material$/i), { target: { value: "PLA" } });
    expect(screen.getByRole("button", { name: /create job/i })).toBeEnabled();

    fireEvent.change(fileInput, {
      target: { files: [new File(["G28\n"], "replacement.gcode", { type: "text/x.gcode" })] },
    });

    expect(await screen.findByText(/uploading/i)).toBeVisible();
    expect(fileInput).toBeDisabled();
    expect(screen.getByRole("button", { name: /create job/i })).toBeDisabled();
  });
});
