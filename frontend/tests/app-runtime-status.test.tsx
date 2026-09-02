import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "../src/app";


afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.resetAllMocks();
});


it("presents backend runtime details in a card-based complementary status region", async () => {
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

  await screen.findByRole("heading", { name: /guided import/i });
  const runtimeStatus = screen.getByRole("complementary", { name: /backend runtime status/i });

  expect(runtimeStatus).toHaveClass("border-slate-200", "bg-white");
  expect(within(runtimeStatus).getByText("print-job-manager")).toBeVisible();
  expect(within(runtimeStatus).getByText("ok")).toBeVisible();
});
