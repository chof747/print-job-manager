export async function fetchBackendHealth(apiBaseUrl: string): Promise<unknown> {
  const response = await fetch(`${apiBaseUrl}/health`);

  if (!response.ok) {
    throw new Error(`Failed to fetch backend health: ${response.status}`);
  }

  return response.json();
}


export async function fetchBackendConfig(apiBaseUrl: string): Promise<unknown> {
  const response = await fetch(`${apiBaseUrl}/config`);

  if (!response.ok) {
    throw new Error(`Failed to fetch backend config: ${response.status}`);
  }

  return response.json();
}
