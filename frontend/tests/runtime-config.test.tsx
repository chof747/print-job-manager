import { expect, it, vi } from "vitest";

import { loadRuntimeConfig } from "../src/runtime-config";


it("rejects when runtime config is missing apiBaseUrl", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({}),
    }),
  );

  await expect(loadRuntimeConfig()).rejects.toThrow(/apiBaseUrl/i);
});


it("rejects with request failure details when the runtime config request fails", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ message: "server error" }),
    }),
  );

  await expect(loadRuntimeConfig()).rejects.toThrow(/500|failed/i);
});
