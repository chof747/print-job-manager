import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RuntimeConfigGate } from "../src/runtime-config-gate";


const { loadRuntimeConfig } = vi.hoisted(() => ({
  loadRuntimeConfig: vi.fn(),
}));


vi.mock("../src/runtime-config", () => ({
  loadRuntimeConfig,
}));


describe("RuntimeConfigGate", () => {
  it("does not render app content until runtime config has loaded", () => {
    loadRuntimeConfig.mockReturnValue(new Promise(() => undefined));

    render(
      <RuntimeConfigGate>
        <div>App Ready</div>
      </RuntimeConfigGate>,
    );

    expect(screen.queryByText("App Ready")).not.toBeInTheDocument();
  });

  it("shows a startup error message when runtime config loading fails", async () => {
    loadRuntimeConfig.mockRejectedValue(new Error("Failed to load runtime config: 500"));

    render(
      <RuntimeConfigGate>
        <div>App Ready</div>
      </RuntimeConfigGate>,
    );

    expect(await screen.findByText(/failed to load runtime config/i)).toBeInTheDocument();
    expect(screen.queryByText("App Ready")).not.toBeInTheDocument();
  });
});
