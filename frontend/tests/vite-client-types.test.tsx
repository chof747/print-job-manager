import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, it } from "vitest";


it("declares Vite client types for the app stylesheet import", () => {
  const declarationPath = resolve(import.meta.dirname, "../src/vite-env.d.ts");

  expect(existsSync(declarationPath)).toBe(true);
  if (!existsSync(declarationPath)) {
    return;
  }

  expect(readFileSync(declarationPath, "utf8")).toMatch(/<reference types="vite\/client"\s*\/>/);
});
