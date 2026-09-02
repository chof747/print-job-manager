import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "../src/app";


const apiBaseUrl = "http://localhost:8000/api/v1";


afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.resetAllMocks();
});


it("gives keyboard-focused workflow controls a visible Tailwind focus ring", async () => {
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
          missingPlanningValues: ["material"],
        }),
      };
    }

    throw new Error(`Unexpected fetch: ${url}`);
  }));

  render(<App />);

  const fileInput = await screen.findByLabelText(/g-code file/i);
  fileInput.focus();
  expect(fileInput).toHaveFocus();
  expect(fileInput).toHaveClass("focus-visible:ring-2", "focus-visible:ring-cyan-400");

  fireEvent.change(fileInput, { target: { files: [new File(["G28\n"], "calibration-cube.gcode")] } });
  fireEvent.change(await screen.findByLabelText(/^material$/i), { target: { value: "PLA" } });

  const createButton = screen.getByRole("button", { name: /create job/i });
  createButton.focus();
  expect(createButton).toHaveFocus();
  expect(createButton).toHaveClass("focus-visible:ring-2", "focus-visible:ring-cyan-400");
});
