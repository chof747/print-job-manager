import { Fragment, useContext, useEffect, useRef, useState } from "react";

import { fetchBackendConfig, fetchBackendHealth } from "./backend-health";
import { loadRuntimeConfig } from "./runtime-config";
import { BootstrapStateCacheContext, RuntimeConfigContext } from "./runtime-config-gate";
import { useJobImport } from "./use-job-import";


export function App() {
  const runtimeConfig = useContext(RuntimeConfigContext);
  const bootstrapStateCache = useContext(BootstrapStateCacheContext);
  const hasBootstrappedSuccessfully = useRef(false);
  const [status, setStatus] = useState<string | null>(bootstrapStateCache?.value?.status ?? null);
  const [appName, setAppName] = useState<string | null>(bootstrapStateCache?.value?.appName ?? null);
  const [apiBaseUrl, setApiBaseUrl] = useState<string | null>(bootstrapStateCache?.value?.apiBaseUrl ?? null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [planningValues, setPlanningValues] = useState<Record<string, string>>({});
  const { artifact, missingPlanningValues, jobs, createError, isImporting, importFile, create } = useJobImport(apiBaseUrl);

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

  async function handleImportGcode(file: File | undefined) {
    if (!file) {
      return;
    }

    try {
      await importFile(file);
      setImportError(null);
      setPlanningValues({});
    } catch (error: unknown) {
      setImportError(error instanceof Error ? error.message : "Unable to import G-code");
    }
  }

  async function handleCreateJob() {
    if (!artifact || missingPlanningValues.some((value) => !planningValues[value]?.trim())) {
      return;
    }

    await create(artifact.id, planningValues);
  }

  const formatPlanningValueLabel = (value: string) => value.replace(/([a-z])([A-Z])/g, "$1 $2");
  const hasBlankPlanningValue = missingPlanningValues.some((value) => !planningValues[value]?.trim());

  return (
    <div>
      <div>{`Backend app: ${appName}`}</div>
      <div>{`API base URL: ${apiBaseUrl}`}</div>
      <div>{`Backend status: ${status}`}</div>
      <label>
        G-code file
        <input
          type="file"
          accept=".gcode"
          aria-label="G-code file"
          disabled={isImporting}
          onChange={(event) => void handleImportGcode(event.target.files?.[0])}
        />
      </label>
      {isImporting && <p>Uploading G-code...</p>}
      {importError && <p role="alert">{importError}</p>}
      {artifact && missingPlanningValues.map((value) => (
        <Fragment key={value}>
          <p>{`${formatPlanningValueLabel(value)} is required.`}</p>
          <label>
            {formatPlanningValueLabel(value)}
            <input
              value={planningValues[value] ?? ""}
              onChange={(event) => setPlanningValues({ ...planningValues, [value]: event.target.value })}
            />
          </label>
        </Fragment>
      ))}
      {artifact && (
        <>
          <button type="button" disabled={isImporting || hasBlankPlanningValue} onClick={() => void handleCreateJob()}>
            Create job
          </button>
          {createError && <p>{createError}</p>}
        </>
      )}
      {jobs.length > 0 && (
        <section>
          <h2>Active queue</h2>
          {jobs.map((job) => (
            <div key={job.id}>
              <div>{job.executionData.artifactRef === artifact?.id ? artifact.filename : job.executionData.artifactRef}</div>
              <div>{job.state}</div>
            </div>
          ))}
        </section>
      )}
    </div>
  );
}
