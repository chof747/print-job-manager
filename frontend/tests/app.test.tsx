import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "../src/app";


const { loadRuntimeConfig, fetchBackendHealth, fetchBackendConfig } = vi.hoisted(() => ({
  loadRuntimeConfig: vi.fn(),
  fetchBackendHealth: vi.fn(),
  fetchBackendConfig: vi.fn(),
}));


vi.mock("../src/runtime-config", () => ({
  loadRuntimeConfig,
}));

vi.mock("../src/backend-health", () => ({
  fetchBackendHealth,
  fetchBackendConfig,
}));


afterEach(async () => {
  cleanup();
  vi.resetAllMocks();

  await new Promise((resolve) => {
    window.setTimeout(resolve, 0);
  });
});


describe("App", () => {
  it("shows the runtime-configured API base URL after loading runtime config", async () => {
    loadRuntimeConfig.mockResolvedValue({
      apiBaseUrl: "http://localhost:8000/api/v1",
    });
    fetchBackendHealth.mockResolvedValue({
      status: "ok",
    });
    fetchBackendConfig.mockResolvedValue({
      appName: "print-job-manager",
      apiBasePath: "/api/v1",
    });

    render(<App />);

    expect(await screen.findByText("print-job-manager")).toBeInTheDocument();
    expect(await screen.findByText("http://localhost:8000/api/v1")).toBeInTheDocument();
    expect(await screen.findByText("ok")).toBeInTheDocument();
  });

  it("shows a startup error message when backend bootstrap requests fail", async () => {
    loadRuntimeConfig.mockResolvedValue({
      apiBaseUrl: "http://localhost:8000/api/v1",
    });
    fetchBackendHealth.mockRejectedValue(new Error("Failed to fetch backend health: 503"));
    fetchBackendConfig.mockResolvedValue({
      appName: "print-job-manager",
      apiBasePath: "/api/v1",
    });

    render(<App />);

    expect(await screen.findByText(/failed to fetch backend health/i)).toBeInTheDocument();
    expect(screen.queryByText("ok")).not.toBeInTheDocument();
  });
});
