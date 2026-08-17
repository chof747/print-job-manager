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
const existingWorktreePath = process.env.SANDCASTLE_EXISTING_WORKTREE_PATH;
const containerUid = Number(process.env.SANDCASTLE_CONTAINER_UID ?? "1000");
const containerGid = Number(process.env.SANDCASTLE_CONTAINER_GID ?? "1000");
const idleTimeoutSeconds = Number(process.env.SANDCASTLE_IDLE_TIMEOUT_SECONDS ?? "1800");
const maxIterations = Number(process.env.SANDCASTLE_MAX_ITERATIONS ?? "5");
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

const slugify = (title: string) => {
  const fillerWords = new Set(["a", "an", "and", "for", "implement", "the", "to"]);

  const words = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .split(/\s+/)
    .filter((word) => word && !fillerWords.has(word))
    .slice(0, 6);

  return words.join("-") || "update";
};

const getIssueBranchPrefix = (issue: GitHubIssue) => {
  const labels = issue.labels.map((label) => label.name.toLowerCase());

  if (labels.includes("bug")) {
    return "bug";
  }

  if (labels.includes("enhancement")) {
    return "feat";
  }

  return "issue";
};

const getIssueBranchName = (issue: GitHubIssue) =>
  `${getIssueBranchPrefix(issue)}/issue-${issue.number}-${slugify(issue.title)}`;

const buildIssuePrompt = (issue: GitHubIssue) => `Work in this repository as the ralph-loop orchestrator.

Implement GitHub issue #${issue.number}: ${issue.title}
${issue.url}

# Ralph Loop Instructions

Before starting implementation, read and follow these files:

- .sandcastle/ralph-orchestrator.md
- .sandcastle/agents/tester.md
- .sandcastle/agents/coder.md
- .sandcastle/agents/reviewer.md
- .sandcastle/agents/handover.md
- docs/TECH_STACK.md

Do not inline or repeat these files in your responses. Keep orchestrator messages concise.

Issue body:
${issue.body || "(empty)"}

Issue comments:
${
  issue.comments.length > 0
    ? issue.comments.map((comment, index) => `Comment ${index + 1}:\n${comment.body}`).join("\n\n")
    : "(none)"
}

Follow the project context in docs/CONTEXT.md, docs/TECH_STACK.md, and docs/architecture/overview.md.
Keep changes minimal and pragmatic.
Do not directly implement production code or write tests as the orchestrator.
Coordinate the tester, coder, reviewer, and handover roles according to the Ralph Loop Instructions.

Completion gate:

Do not output <promise>COMPLETE</promise> after implementation/checks only. You may output <promise>COMPLETE</promise> only after the finalization flow is complete: final QA checklist gathered, final review completed, all AFK findings fixed, changes committed, branch pushed, PR created, PR body includes Closes #${issue.number} and the QA checklist, handover comment posted on the PR, issue labels updated, and any HILT findings documented on the PR.

If you cannot create the PR or update GitHub, do not output <promise>COMPLETE</promise>. Report the blocker instead.`;

const buildResumePrompt = (issue: GitHubIssue) => `Work in this existing preserved Sandcastle worktree as the ralph-loop orchestrator.

Continue GitHub issue #${issue.number}: ${issue.title}
${issue.url}

This is a resume after an interrupted AFK run. Do not restart the issue from scratch.

First inspect:

- git status --short
- git log --oneline -5
- existing backend/frontend files and tests relevant to the issue

Then reconstruct the current behavior state from the worktree and continue with the next smallest unfinished behavior.

Before continuing implementation, read and follow these files when present:

- .sandcastle/ralph-orchestrator.md
- .sandcastle/agents/tester.md
- .sandcastle/agents/coder.md
- .sandcastle/agents/reviewer.md
- .sandcastle/agents/handover.md
- docs/TECH_STACK.md

If docs/TECH_STACK.md is not present in this older worktree, use the accepted stack from issue #31: Python/FastAPI backend, pytest backend tests, React/Vite/TypeScript frontend, Vitest/React Testing Library frontend tests, and Playwright only for critical flows.

If .sandcastle/agents/tester.md is not present in this older worktree, use this fallback test-appropriateness rule: committed tests must not invoke recursive check commands, package-manager install commands, dev servers, watchers, or the same test command currently running. Replace such tests with static assertions, such as parsing package.json for expected script keys and command shapes. Verify dev-server startup with bounded smoke commands during the run and include those steps in the final QA checklist instead of committing server-startup tests.

Do not inline or repeat instruction files in your responses. Keep orchestrator messages concise.
Use per-turn ownership guard snapshots, not git stash snapshots or --base checks.

Current remediation instruction:

If the existing worktree contains committed or uncommitted tests that run npm run check:*, npm run dev:*, pytest, vitest, pip install, npm install, vite, uvicorn, or long-running server/watch commands, treat those tests as invalid tester output. Route the fix to the tester: replace them with static assertions for developer command existence/shape, and move dev-server startup verification into the final QA checklist.

Resume finalization contract:

- Do not treat implementation/checks as complete.
- Before final completion, obtain or construct a final manual QA checklist for the PR body.
- Run or summarize final review status. Fix all AFK findings before PR creation. HILT findings do not block PR creation, but require a draft PR and a separate HILT findings PR comment.
- Commit once with a concise issue-based message.
- Push the current branch.
- Create a PR whose body includes Closes #${issue.number}, implemented behavior summary, automated verification, and the full manual QA checklist.
- Post a separate handover PR comment.
- Remove ready-for-agent from the issue.
- Add ready-for-qa when no HILT findings remain, or needs-info when HILT findings remain. Create only those labels if missing.

Issue body:
${issue.body || "(empty)"}

Issue comments:
${
  issue.comments.length > 0
    ? issue.comments.map((comment, index) => `Comment ${index + 1}:\n${comment.body}`).join("\n\n")
    : "(none)"
}

Completion gate:

Do not output <promise>COMPLETE</promise> after implementation/checks only. You may output <promise>COMPLETE</promise> only after the finalization flow is complete: final QA checklist gathered, final review completed, all AFK findings fixed, changes committed, branch pushed, PR created, PR body includes Closes #${issue.number} and the QA checklist, handover comment posted on the PR, issue labels updated, and any HILT findings documented on the PR.

If you cannot create the PR or update GitHub, do not output <promise>COMPLETE</promise>. Report the blocker instead.`;

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

const selectedIssue = process.env.SANDCASTLE_PROMPT
  ? undefined
  : process.env.SANDCASTLE_ISSUE_NUMBER
    ? getIssue(process.env.SANDCASTLE_ISSUE_NUMBER)
    : getNextIssue();

const prompt = process.env.SANDCASTLE_PROMPT ?? (existingWorktreePath ? buildResumePrompt(selectedIssue!) : buildIssuePrompt(selectedIssue!));
const branchStrategy = selectedIssue
  ? existingWorktreePath
    ? { type: "head" as const }
    : { type: "branch" as const, branch: getIssueBranchName(selectedIssue) }
  : { type: "merge-to-head" as const };

if (process.env.SANDCASTLE_DRY_RUN === "true") {
  console.log(prompt);
  process.exit(0);
}

await run({
  agent: opencode("openai/gpt-5.4"),
  branchStrategy,
  ...(existingWorktreePath ? { cwd: existingWorktreePath } : {}),
  idleTimeoutSeconds,
  maxIterations,
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
