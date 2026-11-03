import { readFileSync } from "node:fs";
import { expect, it } from "vitest";

it("declares React Hook Form for the scheduling edit form", () => {
  const manifest = JSON.parse(readFileSync("package.json", "utf8")) as {
    dependencies?: Record<string, string>;
    devDependencies?: Record<string, string>;
  };

  expect({ ...manifest.dependencies, ...manifest.devDependencies }).toHaveProperty("react-hook-form");
});
