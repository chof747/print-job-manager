import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "../src/app";


const apiBaseUrl = "http://localhost:8000/api/v1";


afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.resetAllMocks();
});


it("limits the operations shell to API-backed import and queue surfaces", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
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

    throw new Error(`Unexpected API request: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  expect(await screen.findByRole("region", { name: /guided import/i })).toBeVisible();
  expect(screen.getByRole("region", { name: /active queue/i })).toBeVisible();
  expect(screen.queryByRole("heading", { name: /printer|scheduler|material stock|job details/i })).not.toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(3);
});
