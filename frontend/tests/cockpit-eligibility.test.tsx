import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "../src/app";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("explains why an active job is blocked for a printer", async () => {
  const base = "http://localhost:8000/api/v1";
  const job = {
    id: "job-1", state: "ready", version: 0,
    executionData: { artifactRef: "artifact-1", artifactFilename: "part.gcode", material: "PLA", requirements: { enclosure: true } },
    schedulingData: { priority: 0 },
  };
  const json = (body: unknown) => ({ ok: true, status: 200, headers: { get: () => "application/json" }, json: async () => body });
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/runtime-config.json") return json({ apiBaseUrl: base });
    if (url === `${base}/health`) return json({ status: "ok" });
    if (url === `${base}/config`) return json({ appName: "print-job-manager" });
    if (url === `${base}/printers`) return json(["printer-1"]);
    if (url === `${base}/queue`) return json({ jobs: [job] });
    if (url === `${base}/cockpit`) return json({ activeJobs: [job], failures: [], recentHistory: [] });
    if (url === `${base}/jobs/job-1`) return json(job);
    if (url === `${base}/jobs/job-1/eligibility` && init?.method === "POST") {
      expect(JSON.parse(String(init.body))).toMatchObject({ printer: { id: "printer-1" } });
      return json({ eligible: false, failures: [{ code: "enclosure_required" }] });
    }
    throw new Error(`Unexpected fetch: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  const active = await screen.findByRole("region", { name: /active/i });
  await within(active).findByText("part.gcode");
  fireEvent.click(within(active).getByRole("button", { name: /details/i }));
  const details = await screen.findByRole("region", { name: /job details/i });
  fireEvent.click(within(details).getByRole("button", { name: /check eligibility/i }));
  expect(within(details).getByRole("alert")).toHaveTextContent("Select a printer");
  expect(within(details).getByLabelText(/printer id/i)).toHaveAttribute("aria-invalid", "true");
  expect(within(details).getByRole("alert")).toHaveClass("bg-red-50", "border-red-300");
  await within(details).findByRole("option", { name: "printer-1" });
  fireEvent.change(within(details).getByLabelText(/printer id/i), { target: { value: "printer-1" } });
  fireEvent.click(within(details).getByRole("button", { name: /check eligibility/i }));

  const dialog = await screen.findByRole("dialog", { name: "Job blocked" });
  expect(within(dialog).getByText(/enclosure.*required|required.*enclosure/i)).toBeVisible();
  expect(dialog).toHaveTextContent(/blocked/i);
  expect(dialog).toHaveTextContent("printer-1");
  fireEvent.click(within(dialog).getByRole("button", { name: "Close" }));
  expect(screen.queryByRole("dialog", { name: "Job blocked" })).not.toBeInTheDocument();
});
