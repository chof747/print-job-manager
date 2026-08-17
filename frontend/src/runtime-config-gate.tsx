import { createContext, type ReactNode, useEffect, useState } from "react";

import { loadRuntimeConfig, type RuntimeConfig } from "./runtime-config";


export type BootstrapState = {
  status: string;
  appName: string;
  apiBaseUrl: string;
};

type BootstrapStateCache = {
  value: BootstrapState | null;
};


type RuntimeConfigGateProps = {
  children: ReactNode;
};


export const RuntimeConfigContext = createContext<RuntimeConfig | null>(null);
export const BootstrapStateCacheContext = createContext<BootstrapStateCache | null>(null);

let cachedRuntimeConfig: RuntimeConfig | null = null;
let runtimeConfigRequest: Promise<RuntimeConfig> | null = null;


export function RuntimeConfigGate({ children }: RuntimeConfigGateProps) {
  const [bootstrapStateCache] = useState<BootstrapStateCache>({ value: null });
  const [config, setConfig] = useState<RuntimeConfig | null>(cachedRuntimeConfig);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    if (!runtimeConfigRequest) {
      runtimeConfigRequest = loadRuntimeConfig().then((loadedConfig) => {
        cachedRuntimeConfig = loadedConfig;
        return loadedConfig;
      });
    }

    void runtimeConfigRequest
      .then((loadedConfig) => {
        runtimeConfigRequest = Promise.resolve(loadedConfig);

        if (isActive) {
          setConfig(loadedConfig);
        }
      })
      .catch((error: unknown) => {
        runtimeConfigRequest = null;

        if (cachedRuntimeConfig) {
          if (isActive) {
            setConfig(cachedRuntimeConfig);
          }

          return;
        }

        if (isActive) {
          setErrorMessage(error instanceof Error ? error.message : "Failed to load runtime config");
        }
      });

    return () => {
      isActive = false;
    };
  }, []);

  if (errorMessage) {
    return <>{errorMessage}</>;
  }

  if (!config) {
    return null;
  }

  return (
    <RuntimeConfigContext.Provider value={config}>
      <BootstrapStateCacheContext.Provider value={bootstrapStateCache}>{children}</BootstrapStateCacheContext.Provider>
    </RuntimeConfigContext.Provider>
  );
}
