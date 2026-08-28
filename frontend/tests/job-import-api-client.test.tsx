import { expect, it, vi } from "vitest";

import { createJob } from "../src/job-import-api-client";


it("sends a JSON create-job request", async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      id: "job-calibration-cube",
      state: "ready",
      executionData: { artifactRef: "calibration-cube" },
    }),
  });
  vi.stubGlobal("fetch", fetchMock);

  await createJob("/api/v1", "calibration-cube", { material: "PLA" });

  expect(fetchMock).toHaveBeenCalledWith("/api/v1/import/calibration-cube/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ material: "PLA" }),
  });
});
