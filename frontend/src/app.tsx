import { useContext, useEffect, useRef, useState } from "react";

import { fetchBackendConfig, fetchBackendHealth } from "./backend-health";
import { loadRuntimeConfig } from "./runtime-config";
import { BootstrapStateCacheContext, RuntimeConfigContext } from "./runtime-config-gate";


export function App() {
  const runtimeConfig = useContext(RuntimeConfigContext);
  const bootstrapStateCache = useContext(BootstrapStateCacheContext);
  const hasBootstrappedSuccessfully = useRef(false);
  const [status, setStatus] = useState<string | null>(bootstrapStateCache?.value?.status ?? null);
  const [appName, setAppName] = useState<string | null>(bootstrapStateCache?.value?.appName ?? null);
  const [apiBaseUrl, setApiBaseUrl] = useState<string | null>(bootstrapStateCache?.value?.apiBaseUrl ?? null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    void Promise.resolve(runtimeConfig ?? loadRuntimeConfig())
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

        hasBootstrappedSuccessfully.current = true;
        setErrorMessage(null);

        const nextStatus = health && typeof health === "object" && "status" in health ? String(health.status) : "unknown";
        const nextAppName =
          backendConfig && typeof backendConfig === "object" && "appName" in backendConfig
            ? String(backendConfig.appName)
            : "unknown";
        if (bootstrapStateCache) {
          bootstrapStateCache.value = {
            status: nextStatus,
            appName: nextAppName,
            apiBaseUrl,
          };
        }

        setStatus(nextStatus);
        setAppName(nextAppName);
        setApiBaseUrl(apiBaseUrl);
      })
      .catch((error: unknown) => {
        if (isActive && bootstrapStateCache?.value) {
          hasBootstrappedSuccessfully.current = true;
          setErrorMessage(null);
          setStatus(bootstrapStateCache.value.status);
          setAppName(bootstrapStateCache.value.appName);
          setApiBaseUrl(bootstrapStateCache.value.apiBaseUrl);
          return;
        }

        if (isActive && !hasBootstrappedSuccessfully.current) {
          setErrorMessage(error instanceof Error ? error.message : "Failed to bootstrap app");
        }
      });

    return () => {
      isActive = false;
    };
  }, [bootstrapStateCache, runtimeConfig]);

  if (errorMessage) {
    return <>{errorMessage}</>;
  }

  if (status === null || appName === null || apiBaseUrl === null) {
    return null;
  }

  return (
    <div>
      <div>{`Backend app: ${appName}`}</div>
      <div>{`API base URL: ${apiBaseUrl}`}</div>
      <div>{`Backend status: ${status}`}</div>
    </div>
  );
}
