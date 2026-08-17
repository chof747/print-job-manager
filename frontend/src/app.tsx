import { useEffect, useState } from "react";

import { fetchBackendConfig, fetchBackendHealth } from "./backend-health";
import { loadRuntimeConfig } from "./runtime-config";


export function App() {
  const [status, setStatus] = useState<string | null>(null);
  const [appName, setAppName] = useState<string | null>(null);
  const [apiBasePath, setApiBasePath] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    void loadRuntimeConfig()
      .then(async (config) => {
        const [health, backendConfig] = await Promise.all([
          fetchBackendHealth(config.apiBaseUrl),
          fetchBackendConfig(config.apiBaseUrl),
        ]);

        return {
          health,
          backendConfig,
          apiBaseUrl: config.apiBaseUrl,
        };
      })
      .then(({ health, backendConfig, apiBaseUrl }) => {
        if (!isActive) {
          return;
        }

        if (health && typeof health === "object" && "status" in health) {
          setStatus(String(health.status));
        }

        if (backendConfig && typeof backendConfig === "object" && "appName" in backendConfig) {
          setAppName(String(backendConfig.appName));
        } else {
          setAppName("unknown");
        }

        if (backendConfig && typeof backendConfig === "object" && "apiBasePath" in backendConfig) {
          setApiBasePath(String(backendConfig.apiBasePath));
        } else {
          setApiBasePath(apiBaseUrl);
        }
      })
      .catch((error: unknown) => {
        if (isActive) {
          setErrorMessage(error instanceof Error ? error.message : "Failed to bootstrap app");
        }
      });

    return () => {
      isActive = false;
    };
  }, []);

  if (errorMessage) {
    return <>{errorMessage}</>;
  }

  if (status === null || appName === null || apiBasePath === null) {
    return null;
  }

  return (
    <div>
      <div>{`Backend app: ${appName}`}</div>
      <div>{`API base URL: ${apiBasePath}`}</div>
      <div>{`Backend status: ${status}`}</div>
    </div>
  );
}
