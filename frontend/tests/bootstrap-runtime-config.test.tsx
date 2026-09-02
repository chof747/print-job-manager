import { StrictMode } from "react";
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

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
  vi.resetModules();
});


function deferredValue<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });

  return { promise, resolve, reject };
}


async function importBootstrapComponents() {
  const [{ App }, { RuntimeConfigGate }] = await Promise.all([
    import("../src/app"),
    import("../src/runtime-config-gate"),
  ]);

  return { App, RuntimeConfigGate };
}


describe("frontend bootstrap", () => {
  it("keeps the bootstrapped shell when startup work replays under StrictMode and the replayed backend bootstrap fails", async () => {
    const { App, RuntimeConfigGate } = await importBootstrapComponents();

    loadRuntimeConfig.mockResolvedValue({
      apiBaseUrl: "http://localhost:8000/api/v1",
    });
    fetchBackendHealth
      .mockResolvedValueOnce({ status: "ok" })
      .mockResolvedValueOnce({ status: "ok" })
      .mockRejectedValueOnce(new Error("Failed to fetch backend health: 503"))
      .mockRejectedValueOnce(new Error("Failed to fetch backend health: 503"));
    fetchBackendConfig.mockResolvedValue({
      appName: "print-job-manager",
      apiBasePath: "/api/v1",
    });

    const { rerender } = render(
      <StrictMode>
        <RuntimeConfigGate>
          <App key="initial" />
        </RuntimeConfigGate>
      </StrictMode>,
    );

    expect(await screen.findByText("print-job-manager")).toBeInTheDocument();
    expect(screen.getByText("http://localhost:8000/api/v1")).toBeInTheDocument();
    expect(screen.getByText("ok")).toBeInTheDocument();

    rerender(
      <StrictMode>
        <RuntimeConfigGate>
          <App key="replay" />
        </RuntimeConfigGate>
      </StrictMode>,
    );

    await waitFor(() => {
      expect(fetchBackendHealth).toHaveBeenCalledTimes(4);
      expect(screen.getByText("print-job-manager")).toBeInTheDocument();
      expect(screen.queryByText("Failed to fetch backend health: 503")).not.toBeInTheDocument();
    });
  });

  it("shows a startup error when a later remount fails after an earlier shell already bootstrapped", async () => {
    const { App, RuntimeConfigGate } = await importBootstrapComponents();

    loadRuntimeConfig.mockResolvedValue({
      apiBaseUrl: "http://localhost:8000/api/v1",
    });
    fetchBackendHealth
      .mockResolvedValueOnce({ status: "ok" })
      .mockResolvedValueOnce({ status: "ok" })
      .mockRejectedValueOnce(new Error("Failed to fetch backend health: 503"))
      .mockRejectedValueOnce(new Error("Failed to fetch backend health: 503"));
    fetchBackendConfig.mockResolvedValue({
      appName: "print-job-manager",
      apiBasePath: "/api/v1",
    });

    const firstRender = render(
      <StrictMode>
        <RuntimeConfigGate>
          <App />
        </RuntimeConfigGate>
      </StrictMode>,
    );

    expect(await screen.findByText("print-job-manager")).toBeInTheDocument();
    expect(screen.getByText("http://localhost:8000/api/v1")).toBeInTheDocument();
    expect(screen.getByText("ok")).toBeInTheDocument();

    firstRender.unmount();

    render(
      <StrictMode>
        <RuntimeConfigGate>
          <App />
        </RuntimeConfigGate>
      </StrictMode>,
    );

    expect(await screen.findByText("Failed to fetch backend health: 503")).toBeInTheDocument();
    expect(screen.queryByText("ok")).not.toBeInTheDocument();
  });
});
