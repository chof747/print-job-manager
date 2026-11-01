import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "../src/app";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("shows persisted dimensions as meaningful read-only measurements", async () => {
  const apiBaseUrl = "http://localhost:8000/api/v1";
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const json = (body: unknown, status = 200) => ({
      ok: status >= 200 && status < 300, status, json: async () => body,
    });
    if (url === "/runtime-config.json") return json({ apiBaseUrl });
    if (url === `${apiBaseUrl}/health`) return json({ status: "ok" });
    if (url === `${apiBaseUrl}/config`) return json({ appName: "print-job-manager", apiBasePath: "/api/v1" });
    if (url === `${apiBaseUrl}/queue`) return json({ jobs: [] });
    if (url === `${apiBaseUrl}/import` && init?.method === "POST") {
      return json({
        artifact: { id: "cube", filename: "cube.gcode" },
        extractedMetadata: { dimensions: { x: 20, y: 30, z: 40 } },
        provenance: { dimensions: { parser: "prusa-family", sourceKey: "object_dimensions" } },
        missingPlanningValues: ["material"],
        diagnostics: [{ code: "malformed_metadata", sourceKey: "TIME" }],
      }, 201);
    }
    throw new Error(`Unexpected fetch: ${url}`);
  }));

  render(<App />);
  fireEvent.change(await screen.findByLabelText(/g-code file/i), {
    target: { files: [new File(["G28\n"], "cube.gcode", { type: "text/x.gcode" })] },
  });

  const dimensions = await screen.findByLabelText(/dimensions/i);
  expect(dimensions).toHaveAttribute("readonly");
  expect(dimensions).toHaveValue("20 × 30 × 40 mm");
  expect(screen.getByLabelText(/^material$/i)).not.toHaveAttribute("readonly");
  expect(screen.getByText("Malformed metadata: TIME")).toBeVisible();
});
