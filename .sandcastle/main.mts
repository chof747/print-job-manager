import { run, opencode } from "@ai-hero/sandcastle";
import { docker } from "@ai-hero/sandcastle/sandboxes/docker";
import { noSandbox } from "@ai-hero/sandcastle/sandboxes/no-sandbox";
import { execFileSync } from "node:child_process";

type GitHubIssue = {
  number: number;
  title: string;
  body: string;
  url: string;
  labels: { name: string }[];
  comments: { body: string }[];
};

const repo = process.env.SANDCASTLE_REPO ?? "chof747/print-job-manager";
const readyLabel = process.env.SANDCASTLE_READY_LABEL ?? "ready-for-agent";
const containerUid = Number(process.env.SANDCASTLE_CONTAINER_UID ?? "1000");
const containerGid = Number(process.env.SANDCASTLE_CONTAINER_GID ?? "1000");
const minDockerMemoryBytes = Number(
  process.env.SANDCASTLE_MIN_DOCKER_MEMORY_BYTES ?? String(4 * 1024 * 1024 * 1024),
);

const shellEnv = {
  ...process.env,
  GH_TOKEN: process.env.GH_TOKEN ?? process.env.GITHUB_TOKEN,
};

const gh = (args: string[]) =>
  execFileSync("gh", args, {
    encoding: "utf8",
    env: shellEnv,
  }).trim();

const dockerCommand = (args: string[]) =>
  execFileSync("docker", args, {
    encoding: "utf8",
  }).trim();

const assertDockerHasEnoughMemory = () => {
  const memTotal = Number(dockerCommand(["info", "--format", "{{json .MemTotal}}"]));

  if (!Number.isFinite(memTotal) || memTotal >= minDockerMemoryBytes) {
    return;
  }

  const availableGb = (memTotal / 1024 / 1024 / 1024).toFixed(1);
  const requiredGb = (minDockerMemoryBytes / 1024 / 1024 / 1024).toFixed(1);

  throw new Error(
    `Docker only has ${availableGb}GB memory available, but Sandcastle/OpenCode needs about ${requiredGb}GB. ` +
      "Increase Docker Desktop memory in Settings > Resources, then rerun npm run sandcastle:docker. " +
      "To bypass this check, set SANDCASTLE_MIN_DOCKER_MEMORY_BYTES=0.",
  );
};

const getIssue = (issueNumber: string): GitHubIssue =>
  JSON.parse(
    gh([
      "issue",
      "view",
      issueNumber,
      "--repo",
      repo,
      "--json",
      "number,title,body,url,labels,comments",
    ]),
  );

const getNextIssue = (): GitHubIssue => {
  const issues = JSON.parse(
    gh([
      "issue",
      "list",
      "--repo",
      repo,
      "--state",
      "open",
      "--label",
      readyLabel,
      "--limit",
      "100",
      "--json",
      "number,title,body,url,labels,comments",
    ]),
  ) as GitHubIssue[];

  const [issue] = issues.sort((a, b) => a.number - b.number);

  if (!issue) {
    throw new Error(`No open GitHub issues found with label "${readyLabel}" in ${repo}.`);
  }

  return issue;
};

const buildIssuePrompt = (issue: GitHubIssue) => `Work in this repository.

Implement GitHub issue #${issue.number}: ${issue.title}
${issue.url}

Issue body:
${issue.body || "(empty)"}

Issue comments:
${
  issue.comments.length > 0
    ? issue.comments.map((comment, index) => `Comment ${index + 1}:\n${comment.body}`).join("\n\n")
    : "(none)"
}

Follow the project context in docs/CONTEXT.md and docs/architecture/overview.md.
Keep changes minimal and pragmatic.
Run relevant verification.
If the issue is fully implemented, close it with a concise completion comment.
When the task is complete, output <promise>COMPLETE</promise>.`;

const useDockerSandbox = process.env.SANDCASTLE_SANDBOX === "docker";

if (useDockerSandbox) {
  assertDockerHasEnoughMemory();
}

const sandbox = useDockerSandbox
  ? docker({
      imageName: "sandcastle:print-job-manager",
      containerUid,
      containerGid,
      env: {
        HOME: "/home/agent",
        GH_TOKEN: process.env.GH_TOKEN ?? process.env.GITHUB_TOKEN ?? "",
        GITHUB_TOKEN: process.env.GITHUB_TOKEN ?? process.env.GH_TOKEN ?? "",
        XDG_STATE_HOME: "/tmp/opencode-state",
        XDG_CACHE_HOME: "/tmp/opencode-cache",
      },
      mounts: [
        {
          hostPath: "~/.local/share/opencode/auth.json",
          sandboxPath: "/home/agent/host-auth/auth.json",
          readonly: true,
        },
        {
          hostPath: "~/.config/opencode",
          sandboxPath: "/home/agent/.config/opencode",
          readonly: true,
        },
      ],
    })
  : noSandbox();

const prompt =
  process.env.SANDCASTLE_PROMPT ??
  buildIssuePrompt(
    process.env.SANDCASTLE_ISSUE_NUMBER
      ? getIssue(process.env.SANDCASTLE_ISSUE_NUMBER)
      : getNextIssue(),
  );

if (process.env.SANDCASTLE_DRY_RUN === "true") {
  console.log(prompt);
  process.exit(0);
}

await run({
  agent: opencode("openai/gpt-5.4"),
  branchStrategy: { type: "merge-to-head" },
  sandbox,
  ...(useDockerSandbox
    ? {
        hooks: {
          sandbox: {
            onSandboxReady: [
              {
                command:
                  "mkdir -p /tmp/opencode-state /tmp/opencode-cache /home/agent/.local/share/opencode/log && cp /home/agent/host-auth/auth.json /home/agent/.local/share/opencode/auth.json",
              },
            ],
          },
        },
      }
    : {}),
  prompt,
  logging: {
    type: "stdout",
    verbose: true,
  },
});
