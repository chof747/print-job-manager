import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "../src/app";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("creates a job for the selected import rather than shared artifact identity", async () => {
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
        import: { id: "second-import" },
        artifact: { id: "shared-artifact", filename: "second.gcode" },
        extractedMetadata: { material: "PETG" },
        missingPlanningValues: [],
        diagnostics: [],
      }, 201);
    }
    if (url === `${apiBaseUrl}/import/second-import`) {
      return json({
        import: { id: "second-import" },
        artifact: { id: "shared-artifact", filename: "second.gcode" },
        extractedMetadata: { material: "PETG" },
        missingPlanningValues: [],
        diagnostics: [],
      });
    }
    if (url.endsWith("/jobs") && init?.method === "POST") return json({ id: "job-1" }, 201);
    throw new Error(`Unexpected fetch: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  fireEvent.change(await screen.findByLabelText(/g-code file/i), {
    target: { files: [new File(["G28\n"], "second.gcode", { type: "text/x.gcode" })] },
  });
  expect(await screen.findByLabelText(/^material$/i)).toHaveValue("PETG");
  fireEvent.click(screen.getByRole("button", { name: /create job/i }));

  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
    `${apiBaseUrl}/import/second-import/jobs`, expect.objectContaining({ method: "POST" }),
  ));
});
