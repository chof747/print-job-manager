import { type ReactNode, useEffect, useState } from "react";

import { loadRuntimeConfig } from "./runtime-config";


type RuntimeConfigGateProps = {
  children: ReactNode;
};


export function RuntimeConfigGate({ children }: RuntimeConfigGateProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    void loadRuntimeConfig()
      .then(() => {
        if (isActive) {
          setIsLoaded(true);
        }
      })
      .catch((error: unknown) => {
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

  if (!isLoaded) {
    return null;
  }

  return <>{children}</>;
}
