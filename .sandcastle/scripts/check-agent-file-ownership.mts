import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { dirname } from "node:path";

type Role = "tester" | "coder";

type Snapshot = Record<string, string>;

const usage = `Usage: tsx .sandcastle/scripts/check-agent-file-ownership.mts --role <tester|coder> (--snapshot-in <file> | --snapshot-out <file> | --base <ref> --manual-base-mode) [--allow <path-prefix>]...

Checks changed files against ralph-loop tester/coder ownership rules.

Preferred ralph-loop usage:
  1. Before a sub-agent turn: --snapshot-out .sandcastle/tmp/<role>-before.json
  2. After the sub-agent turn: --snapshot-in .sandcastle/tmp/<role>-before.json

The --base mode is retained for coarse manual checks only and requires --manual-base-mode.`;

const args = process.argv.slice(2);
let role: Role | undefined;
let base: string | undefined;
let snapshotIn: string | undefined;
let snapshotOut: string | undefined;
let manualBaseMode = false;
const allowedExceptions: string[] = [];

for (let index = 0; index < args.length; index += 1) {
  const arg = args[index];

  if (arg === "--role") {
    const value = args[index + 1];
    if (value !== "tester" && value !== "coder") {
      throw new Error(`${usage}\n\nInvalid --role: ${value ?? "(missing)"}`);
    }
    role = value;
    index += 1;
    continue;
  }

  if (arg === "--base") {
    base = args[index + 1];
    if (!base) {
      throw new Error(`${usage}\n\nMissing value for --base.`);
    }
    index += 1;
    continue;
  }

  if (arg === "--snapshot-in") {
    snapshotIn = args[index + 1];
    if (!snapshotIn) {
      throw new Error(`${usage}\n\nMissing value for --snapshot-in.`);
    }
    index += 1;
    continue;
  }

  if (arg === "--snapshot-out") {
    snapshotOut = args[index + 1];
    if (!snapshotOut) {
      throw new Error(`${usage}\n\nMissing value for --snapshot-out.`);
    }
    index += 1;
    continue;
  }

  if (arg === "--allow") {
    const value = args[index + 1];
    if (!value) {
      throw new Error(`${usage}\n\nMissing value for --allow.`);
    }
    allowedExceptions.push(normalizePath(value));
    index += 1;
    continue;
  }

  if (arg === "--manual-base-mode") {
    manualBaseMode = true;
    continue;
  }

  throw new Error(`${usage}\n\nUnknown argument: ${arg}`);
}

if (!role) {
  throw new Error(usage);
}

const modeCount = [base, snapshotIn, snapshotOut].filter(Boolean).length;
if (modeCount !== 1) {
  throw new Error(`${usage}\n\nPass exactly one of --base, --snapshot-in, or --snapshot-out.`);
}

if (base && !manualBaseMode) {
  throw new Error(`${usage}\n\n--base is coarse manual mode only. Use --snapshot-out before a sub-agent turn and --snapshot-in after it.`);
}

const testPrefixes = ["backend/tests/", "frontend/tests/", "frontend/e2e/"];
const testerExceptionPrefixes = [
  "package.json",
  "package-lock.json",
  "pnpm-lock.yaml",
  "pyproject.toml",
  "uv.lock",
  "requirements.txt",
  "pytest.ini",
  "vite.config.mjs",
  "vite.config.js",
  "vite.config.ts",
  "vitest.config.mjs",
  "vitest.config.js",
  "vitest.config.ts",
  "playwright.config.ts",
  "playwright.config.js",
];

if (role === "tester") {
  const invalidExceptions = allowedExceptions.filter(
    (allowedPath) => !testerExceptionPrefixes.includes(allowedPath),
  );

  if (invalidExceptions.length > 0) {
    console.error("Tester ownership exceptions are restricted to test harness/dependency config files.");
    console.error("Invalid --allow values:");
    for (const allowedPath of invalidExceptions) {
      console.error(`- ${allowedPath}`);
    }
    process.exit(1);
  }
}

if (snapshotOut) {
  mkdirSync(dirname(snapshotOut), { recursive: true });
  writeFileSync(snapshotOut, JSON.stringify(createSnapshot(), null, 2));
  console.log(`File ownership snapshot written for role: ${role}`);
  console.log(snapshotOut);
  process.exit(0);
}

const changedFiles = snapshotIn ? getFilesChangedSinceSnapshot(snapshotIn) : getFilesChangedSinceBase(base!);

const violations = changedFiles.filter((filePath) => {
  if (isAllowedException(filePath)) {
    return false;
  }

  const isTestFile = testPrefixes.some((prefix) => filePath.startsWith(prefix));

  if (role === "tester") {
    return !isTestFile;
  }

  return isTestFile;
});

const stackViolations = changedFiles.filter((filePath) => {
  if (role !== "tester") {
    return false;
  }

  if (filePath.startsWith("backend/tests/")) {
    return !filePath.endsWith(".py");
  }

  if (filePath.startsWith("frontend/tests/") || filePath.startsWith("frontend/e2e/")) {
    return filePath.endsWith(".py");
  }

  return false;
});

if (violations.length > 0 || stackViolations.length > 0) {
  console.error(`File ownership check failed for role: ${role}`);
  console.error("");
  console.error("Changed files:");
  for (const filePath of changedFiles) {
    console.error(`- ${filePath}`);
  }
  console.error("");
  if (violations.length > 0) {
    console.error("Ownership violations:");
    for (const filePath of violations) {
      console.error(`- ${filePath}`);
    }
    console.error("");
  }

  if (stackViolations.length > 0) {
    console.error("Test stack violations:");
    for (const filePath of stackViolations) {
      console.error(`- ${filePath}`);
    }
    console.error("");
    console.error("Backend tests must use pytest in backend/tests/**/*.py.");
    console.error("Frontend tests must use Vitest/RTL under frontend/tests/** or Playwright under frontend/e2e/**.");
    console.error("");
  }

  console.error("Role rules:");
  console.error("Tester may normally modify only backend/tests/**, frontend/tests/**, and frontend/e2e/**.");
  console.error("Coder may modify anything except those test directories.");
  process.exit(1);
}

console.log(`File ownership check passed for role: ${role}`);
if (changedFiles.length > 0) {
  for (const filePath of changedFiles) {
    console.log(`- ${filePath}`);
  }
}

function normalizePath(filePath: string): string {
  return filePath.replaceAll("\\", "/").replace(/^\.\//, "");
}

function getFilesChangedSinceBase(baseRef: string): string[] {
  return execFileSync("git", ["diff", "--name-only", baseRef, "--"], {
    encoding: "utf8",
  })
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map(normalizePath)
    .filter((filePath) => !filePath.startsWith(".sandcastle/tmp/"));
}

function getFilesChangedSinceSnapshot(snapshotPath: string): string[] {
  const before = JSON.parse(readFileSync(snapshotPath, "utf8")) as Snapshot;
  const after = createSnapshot();
  const filePaths = new Set([...Object.keys(before), ...Object.keys(after)]);

  return [...filePaths].filter((filePath) => before[filePath] !== after[filePath]).sort();
}

function createSnapshot(): Snapshot {
  const files = execFileSync("git", ["ls-files", "--cached", "--others", "--exclude-standard", "-z"], {
    encoding: "utf8",
  })
    .split("\0")
    .map((line) => line.trim())
    .filter(Boolean)
    .map(normalizePath);

  return Object.fromEntries(files.filter(isRegularFile).map((filePath) => [filePath, hashFile(filePath)]));
}

function isRegularFile(filePath: string): boolean {
  return existsSync(filePath) && statSync(filePath).isFile();
}

function hashFile(filePath: string): string {
  return createHash("sha256").update(readFileSync(filePath)).digest("hex");
}

function isAllowedException(filePath: string): boolean {
  return allowedExceptions.some(
    (allowedPath) => filePath === allowedPath || filePath.startsWith(`${allowedPath.replace(/\/$/, "")}/`),
  );
}
