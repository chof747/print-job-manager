import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "../src/app";


afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.resetAllMocks();
});


it("renders the current workflow in a dark operations shell with guided import and active queue panels", async () => {
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

  const shell = await screen.findByRole("main", { name: /operations/i });
  expect(shell).toHaveClass("bg-slate-950");
  expect(within(shell).getByRole("region", { name: /guided import/i })).toContainElement(
    screen.getByLabelText(/g-code file/i),
  );
  expect(within(shell).getByRole("region", { name: /active queue/i })).toBeInTheDocument();
});
