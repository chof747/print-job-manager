import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "../src/app";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("reviews persisted import facts instead of stale upload values", async () => {
  const apiBaseUrl = "http://localhost:8000/api/v1";
  const json = (body: unknown, status = 200) => ({
    ok: status >= 200 && status < 300, status, json: async () => body,
  });
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/runtime-config.json") return json({ apiBaseUrl });
    if (url === `${apiBaseUrl}/health`) return json({ status: "ok" });
    if (url === `${apiBaseUrl}/config`) return json({ appName: "print-job-manager", apiBasePath: "/api/v1" });
    if (url === `${apiBaseUrl}/queue`) return json({ jobs: [] });
    if (url === `${apiBaseUrl}/import` && init?.method === "POST") {
      return json({
        import: { id: "import-2" },
        artifact: { id: "artifact", filename: "cube.gcode" },
        extractedMetadata: { material: "PLA" },
        missingPlanningValues: [],
        diagnostics: [],
      }, 201);
    }
    if (url === `${apiBaseUrl}/import/import-2`) {
      return json({
        import: { id: "import-2" },
        artifact: { id: "artifact", filename: "cube.gcode" },
        extractedMetadata: { estimatedDuration: 60 },
        missingPlanningValues: ["material"],
        diagnostics: [{ code: "conflicting_metadata", sourceKey: "filament_type" }],
      });
    }
    throw new Error(`Unexpected fetch: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  fireEvent.change(await screen.findByLabelText(/g-code file/i), {
    target: { files: [new File(["G28\n"], "cube.gcode", { type: "text/x.gcode" })] },
  });

  expect(await screen.findByText("Conflicting metadata: filament_type")).toBeVisible();
  expect(screen.getByLabelText(/estimated duration/i)).toHaveValue("1m 0s");
  expect(screen.getByLabelText(/^material$/i)).not.toHaveAttribute("readonly");
  expect(screen.getByRole("button", { name: /create job/i })).toBeDisabled();
  expect(fetchMock).toHaveBeenCalledWith(`${apiBaseUrl}/import/import-2`);
});
