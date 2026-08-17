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


afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});


describe("App", () => {
  it("shows backend health after loading runtime config", async () => {
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

    expect(await screen.findByText("Backend app: print-job-manager")).toBeInTheDocument();
    expect(await screen.findByText("API base URL: /api/v1")).toBeInTheDocument();
    expect(await screen.findByText("Backend status: ok")).toBeInTheDocument();
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
    expect(screen.queryByText("Backend status: ok")).not.toBeInTheDocument();
  });
});
