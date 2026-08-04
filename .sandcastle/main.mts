import { run, opencode } from "@ai-hero/sandcastle";
import { docker } from "@ai-hero/sandcastle/sandboxes/docker";
import { noSandbox } from "@ai-hero/sandcastle/sandboxes/no-sandbox";

const useDockerSandbox = process.env.SANDCASTLE_SANDBOX === "docker";

const sandbox = useDockerSandbox
  ? docker({
      imageName: "sandcastle:print-job-manager",
      env: {
        HOME: "/home/agent",
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

const prompt = process.env.SANDCASTLE_PROMPT;

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
  ...(prompt ? { prompt } : { promptFile: ".sandcastle/prompt.md" }),
  logging: {
    type: "stdout",
    verbose: true,
  },
});
