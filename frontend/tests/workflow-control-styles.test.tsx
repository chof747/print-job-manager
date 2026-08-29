import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "../src/app";


const apiBaseUrl = "http://localhost:8000/api/v1";
const controlClasses = ["border", "border-slate-700", "bg-slate-800", "text-slate-100", "focus-visible:ring-2", "focus-visible:ring-cyan-400"];


afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.resetAllMocks();
});


it("styles file, planning, and create controls as dark keyboard-focusable workflow controls", async () => {
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);

    if (url === "/runtime-config.json") {
      return { ok: true, json: async () => ({ apiBaseUrl }) };
    }

    if (url === `${apiBaseUrl}/health`) {
      return { ok: true, json: async () => ({ status: "ok" }) };
    }

    if (url === `${apiBaseUrl}/config`) {
      return { ok: true, json: async () => ({ appName: "print-job-manager", apiBasePath: "/api/v1" }) };
    }

    if (url === `${apiBaseUrl}/import` && init?.method === "POST") {
      return {
        ok: true,
        json: async () => ({
          artifact: { id: "artifact-calibration-cube", filename: "calibration-cube.gcode" },
          missingPlanningValues: ["material", "estimatedDuration"],
        }),
      };
    }

    throw new Error(`Unexpected fetch: ${url}`);
  }));

  render(<App />);

  const fileInput = await screen.findByLabelText(/g-code file/i);
  expect(fileInput).toHaveClass(...controlClasses);

  fireEvent.change(fileInput, { target: { files: [new File(["G28\n"], "calibration-cube.gcode")] } });

  expect(await screen.findByLabelText(/^material$/i)).toHaveClass(...controlClasses);
  expect(screen.getByLabelText(/estimated duration/i)).toHaveClass(...controlClasses);
  expect(screen.getByRole("button", { name: /create job/i })).toHaveClass(...controlClasses);
});
