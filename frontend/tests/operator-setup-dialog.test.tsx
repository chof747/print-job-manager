import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";

import { OperatorSetup } from "../src/operator-setup";

afterEach(cleanup);

it.each([
  ["Set up printer", "Printer setup", "Printer ID"],
  ["Add material", "Material setup", "Material type"],
])("opens %s in a styled dialog and closes it with Escape", (button, title, field) => {
  render(<OperatorSetup apiBaseUrl="/api" />);
  const trigger = screen.getByRole("button", { name: button });
  fireEvent.click(trigger);
  const dialog = screen.getByRole("dialog", { name: title });
  expect(dialog).toHaveAttribute("aria-modal", "true");
  expect(within(dialog).getByLabelText(field)).toHaveClass("border-slate-300", "rounded-xl");
  fireEvent.keyDown(document, { key: "Escape" });
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(trigger).toHaveFocus();
});
