import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { expect, it } from "vitest";

it("routes scheduling updates through an OpenAPI-generated client", () => {
  const filename = resolve("frontend/src/job-import-api-client.ts");
  const source = readFileSync(filename, "utf8");
  const update = source.split("export async function updateJobScheduling")[1] ?? "";
  const imports = [...source.matchAll(/import\s+(?!type\b)([\s\S]*?)\s+from\s+["'](\.[^"']+)["']/g)];
  const usesGeneratedClient = imports.some(([, bindings, specifier]) => {
    const path = resolve(dirname(filename), specifier);
    const generatedFile = [path, `${path}.ts`, `${path}.tsx`, resolve(path, "index.ts")].find(existsSync);
    const names = bindings.match(/[A-Za-z_$][\w$]*/g) ?? [];
    return names.some((name) => new RegExp(`\\b${name}\\b`).test(update)) &&
      !!generatedFile && /generated (?:by|using|from)|@generated/i.test(readFileSync(generatedFile, "utf8"));
  });

  expect(usesGeneratedClient).toBe(true);
});
