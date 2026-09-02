import { cleanup, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";


afterEach(() => {
  cleanup();
  document.body.innerHTML = "";
  vi.unstubAllGlobals();
  vi.resetModules();
});


describe("main entrypoint", () => {
  it("renders the app into #root through the real frontend bootstrap path", async () => {
    document.body.innerHTML = '<div id="root"></div>';

    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);

      if (url === "/runtime-config.json") {
        return {
          ok: true,
          json: async () => ({ apiBaseUrl: "http://localhost:8000/api/v1" }),
        };
      }

      if (url === "http://localhost:8000/api/v1/health") {
        return {
          ok: true,
          json: async () => ({ status: "ok" }),
        };
      }

      if (url === "http://localhost:8000/api/v1/config") {
        return {
          ok: true,
          json: async () => ({ appName: "print-job-manager", apiBasePath: "/api/v1" }),
        };
      }

      throw new Error(`Unexpected fetch: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    await import("../src/main");

    expect(await screen.findByText("print-job-manager")).toBeInTheDocument();
    expect(screen.getByText("http://localhost:8000/api/v1")).toBeInTheDocument();
    expect(screen.getByText("ok")).toBeInTheDocument();
    expect(document.getElementById("root")?.textContent).toContain("print-job-manager");
  });
});
