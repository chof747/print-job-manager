import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, it } from "vitest";


it("requires esbuild's pnpm build approval to be a boolean", () => {
  const workspaceConfig = readFileSync(
    resolve(import.meta.dirname, "../../pnpm-workspace.yaml"),
    "utf8",
  );

  expect(workspaceConfig).toMatch(/^\s*esbuild:\s*(?:true|false)\s*$/m);
});
