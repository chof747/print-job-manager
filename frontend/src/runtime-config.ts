export type RuntimeConfig = {
  apiBaseUrl: string;
};

export async function loadRuntimeConfig(): Promise<RuntimeConfig> {
  const response = await fetch("/runtime-config.json");

  if (!response.ok) {
    throw new Error(`Failed to load runtime config: ${response.status}`);
  }

  const config = await response.json();

  if (!config || typeof config.apiBaseUrl !== "string" || config.apiBaseUrl.length === 0) {
    throw new Error("Runtime config is missing apiBaseUrl");
  }

  return config;
}
