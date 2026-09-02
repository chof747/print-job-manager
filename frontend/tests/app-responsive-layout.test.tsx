import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "../src/app";


afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.resetAllMocks();
});


it("keeps the import shell in one column on mobile and adds a runtime side rail on large screens", async () => {
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);

    if (url === "/runtime-config.json") {
      return { ok: true, json: async () => ({ apiBaseUrl: "http://localhost:8000/api/v1" }) };
    }

    if (url === "http://localhost:8000/api/v1/health") {
      return { ok: true, json: async () => ({ status: "ok" }) };
    }

    if (url === "http://localhost:8000/api/v1/config") {
      return { ok: true, json: async () => ({ appName: "print-job-manager", apiBasePath: "/api/v1" }) };
    }

    throw new Error(`Unexpected fetch: ${url}`);
  }));

  render(<App />);

  const importPanel = await screen.findByRole("region", { name: /guided import/i });
  const queuePanel = screen.getByRole("region", { name: /active queue/i });
  const layout = importPanel.parentElement;

  expect(layout).toContainElement(queuePanel);
  expect(layout).toHaveClass("grid-cols-1", "lg:grid-cols-[minmax(0,1fr)_300px]");
});
