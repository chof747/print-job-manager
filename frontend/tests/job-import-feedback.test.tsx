import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "../src/app";


const apiBaseUrl = "http://localhost:8000/api/v1";
const artifact = { id: "artifact-calibration-cube", filename: "calibration-cube.gcode" };
const job = {
  id: "job-calibration-cube",
  state: "ready",
  executionData: { artifactRef: artifact.id },
};


function jsonResponse(body: unknown, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}


afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.resetAllMocks();
});


it("gives upload, create success, create failure, and queue refresh failure distinct accessible visual feedback", async () => {
  let importCount = 0;
  let createCount = 0;
  let resolveFirstImport: ((response: ReturnType<typeof jsonResponse>) => void) | undefined;
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
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
        return new Promise<ReturnType<typeof jsonResponse>>((resolve) => {
          resolveFirstImport = resolve;
        });
      }

      return Promise.resolve(jsonResponse({ artifact, missingPlanningValues: ["material"] }, 201));
    }

    if (url === `${apiBaseUrl}/import/${artifact.id}/jobs` && init?.method === "POST") {
      createCount += 1;
      if (createCount === 2) {
        return Promise.resolve(jsonResponse({ detail: "Unable to create job" }, 500));
      }

      return Promise.resolve(jsonResponse(job, 201));
    }

    if (url === `${apiBaseUrl}/queue`) {
      return Promise.resolve(createCount === 3 ? jsonResponse({}, 500) : jsonResponse({ jobs: [job] }));
    }

    throw new Error(`Unexpected fetch: ${url}`);
  }));

  render(<App />);

  const fileInput = await screen.findByLabelText(/g-code file/i);
  fireEvent.change(fileInput, { target: { files: [new File(["G28\n"], "first.gcode")] } });
  const loadingFeedback = await screen.findByRole("status", { name: /uploading g-code/i });
  expect(loadingFeedback).toHaveClass("border-indigo-200", "bg-indigo-100", "text-indigo-800");

  resolveFirstImport?.(jsonResponse({ artifact, missingPlanningValues: ["material"] }, 201));
  await screen.findByLabelText(/^material$/i);

  async function createFromImportedFile(filename: string) {
    fireEvent.change(screen.getByLabelText(/g-code file/i), {
      target: { files: [new File(["G28\n"], filename)] },
    });
    fireEvent.change(await screen.findByLabelText(/^material$/i), { target: { value: "PLA" } });
    fireEvent.click(screen.getByRole("button", { name: /create job/i }));
  }

  await createFromImportedFile("second.gcode");
  const successFeedback = await screen.findByRole("status", { name: /job created/i });
  expect(successFeedback).toHaveClass("border-emerald-200", "bg-emerald-50", "text-emerald-800");

  await createFromImportedFile("third.gcode");
  const createFailure = await screen.findByRole("alert");
  expect(createFailure).toHaveTextContent("Unable to create job");
  expect(createFailure).toHaveClass("border-rose-200", "bg-rose-50", "text-rose-800");

  await createFromImportedFile("fourth.gcode");
  const queueRefreshFailure = await screen.findByRole("alert");
  expect(queueRefreshFailure).toHaveTextContent(
    "Job was created, but the active queue could not be refreshed",
  );
  expect(queueRefreshFailure).toHaveClass("border-rose-200", "bg-rose-50", "text-rose-800");
});
