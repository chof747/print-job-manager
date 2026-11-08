import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { OperatorSetup } from "../src/operator-setup";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("saves material attributes and confirms success", async () => {
  const fetchMock = vi.fn(async () => ({ ok: true }));
  vi.stubGlobal("fetch", fetchMock);
  render(<OperatorSetup apiBaseUrl="http://localhost:8000/api/v1" />);

  fireEvent.click(screen.getByRole("button", { name: /add material/i }));
  const form = screen.getByRole("region", { name: /material setup/i });
  fireEvent.change(within(form).getByLabelText(/material type/i), { target: { value: " PLA " } });
  fireEvent.change(within(form).getByLabelText(/color/i), { target: { value: " black " } });
  fireEvent.change(within(form).getByLabelText(/amount/i), { target: { value: "125.5" } });
  fireEvent.click(within(form).getByRole("button", { name: /save material/i }));

  expect(await within(form).findByRole("status")).toHaveTextContent(/material saved/i);
  expect(fetchMock).toHaveBeenCalledOnce();
  const [url, request] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
  expect(url).toBe("http://localhost:8000/api/v1/inventory/materials");
  expect(request.method).toBe("POST");
  expect(JSON.parse(String(request.body))).toEqual({ materialType: "PLA", color: "black", amountGrams: 125.5 });
});
