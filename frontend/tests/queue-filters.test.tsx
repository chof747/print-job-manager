import { useState } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";

import { QueueFilters } from "../src/queue-filters";

afterEach(cleanup);

it("keeps drafts across categories, applies them together, and clears them", () => {
  function Example() {
    const [applied, setApplied] = useState("");
    return <QueueFilters applied={applied} onApply={setApplied} />;
  }
  render(<Example />);
  expect(screen.getByText("No filters applied")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Open filter rail" }));
  fireEvent.change(screen.getByLabelText("Filter by material"), { target: { value: " PLA " } });
  fireEvent.click(screen.getByRole("button", { name: "Print requirements" }));
  fireEvent.change(screen.getByLabelText("Nozzle diameter (mm)"), { target: { value: "0.4" } });
  fireEvent.click(screen.getByRole("button", { name: "Apply filters" }));
  expect(screen.getByText("2 active filters")).toBeInTheDocument();
  expect(screen.getByText("Filter by material: PLA")).toBeInTheDocument();
  expect(screen.getByText("Nozzle diameter (mm): 0.4")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Open filter rail" }));
  expect(screen.getByLabelText("Nozzle diameter (mm)")).toHaveValue(0.4);
  fireEvent.click(screen.getByRole("button", { name: "Clear all" }));
  expect(screen.getByText("No filters applied")).toBeInTheDocument();
  expect(screen.getByLabelText("Nozzle diameter (mm)")).toHaveValue(null);
});
