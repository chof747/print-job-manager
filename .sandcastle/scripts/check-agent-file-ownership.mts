import { execFileSync } from "node:child_process";

type Role = "tester" | "coder";

const usage = `Usage: tsx .sandcastle/scripts/check-agent-file-ownership.mts --role <tester|coder> --base <ref> [--allow <path-prefix>]...

Checks changed files since --base against ralph-loop tester/coder ownership rules.`;

const args = process.argv.slice(2);
let role: Role | undefined;
let base: string | undefined;
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

  if (arg === "--allow") {
    const value = args[index + 1];
    if (!value) {
      throw new Error(`${usage}\n\nMissing value for --allow.`);
    }
    allowedExceptions.push(normalizePath(value));
    index += 1;
    continue;
  }

  throw new Error(`${usage}\n\nUnknown argument: ${arg}`);
}

if (!role || !base) {
  throw new Error(usage);
}

const testPrefixes = ["backend/tests/", "frontend/tests/", "frontend/e2e/"];

const changedFiles = execFileSync("git", ["diff", "--name-only", base, "--"], {
  encoding: "utf8",
})
  .split("\n")
  .map((line) => line.trim())
  .filter(Boolean)
  .map(normalizePath);

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

if (violations.length > 0) {
  console.error(`File ownership check failed for role: ${role}`);
  console.error("");
  console.error("Changed files:");
  for (const filePath of changedFiles) {
    console.error(`- ${filePath}`);
  }
  console.error("");
  console.error("Violations:");
  for (const filePath of violations) {
    console.error(`- ${filePath}`);
  }
  console.error("");
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

function isAllowedException(filePath: string): boolean {
  return allowedExceptions.some(
    (allowedPath) => filePath === allowedPath || filePath.startsWith(`${allowedPath.replace(/\/$/, "")}/`),
  );
}
