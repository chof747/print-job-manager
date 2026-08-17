import { expect, it, vi } from "vitest";

import { fetchBackendConfig, fetchBackendHealth } from "../src/backend-health";


it("calls the backend health endpoint using the configured api base URL", async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ status: "ok" }),
  });

  vi.stubGlobal("fetch", fetchMock);

  await fetchBackendHealth("http://localhost:8000/api/v1");

  expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/v1/health");
});


it("calls the backend config endpoint using the configured api base URL", async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ appName: "print-job-manager", apiBasePath: "/api/v1" }),
  });

  vi.stubGlobal("fetch", fetchMock);

  await fetchBackendConfig("http://localhost:8000/api/v1");

  expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/v1/config");
});


it("rejects with request failure details when the backend health request fails", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ message: "service unavailable" }),
    }),
  );

  await expect(fetchBackendHealth("http://localhost:8000/api/v1")).rejects.toThrow(/503|failed/i);
});


it("rejects with request failure details when the backend config request fails", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      status: 502,
      json: async () => ({ message: "bad gateway" }),
    }),
  );

  await expect(fetchBackendConfig("http://localhost:8000/api/v1")).rejects.toThrow(/502|failed/i);
});
