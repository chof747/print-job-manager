import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, it } from "vitest";


it("ships Tailwind through the Vite plugin and the app entrypoint stylesheet", () => {
  const frontendRoot = resolve(import.meta.dirname, "..");
  const viteConfig = readFileSync(resolve(frontendRoot, "vite.config.mts"), "utf8");
  const appEntrypoint = readFileSync(resolve(frontendRoot, "src/main.tsx"), "utf8");
  const appStyles = readFileSync(resolve(frontendRoot, "src/app.css"), "utf8");

  expect(viteConfig).toMatch(/import tailwindcss from "@tailwindcss\/vite"/);
  expect(viteConfig).toMatch(/plugins:\s*\[tailwindcss\(\)\]/);
  expect(appEntrypoint).toMatch(/import "\.\/app\.css"/);
  expect(appStyles).toMatch(/@import "tailwindcss"/);
});
