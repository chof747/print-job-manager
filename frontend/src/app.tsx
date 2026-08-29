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
  const { artifact, missingPlanningValues, jobs, createError, isCreated, isImporting, importFile, create } = useJobImport(apiBaseUrl);

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
    <main aria-label="Operations" className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto grid max-w-7xl grid-cols-1 gap-4 p-4 lg:grid-cols-2">
        <section aria-labelledby="guided-import-heading" className="rounded-lg border border-slate-800 bg-slate-900 p-4">
          <h1 id="guided-import-heading">Guided import</h1>
          <label>
            G-code file
            <input
              type="file"
              accept=".gcode"
              aria-label="G-code file"
              className="border border-slate-700 bg-slate-800 text-slate-100 focus-visible:ring-2 focus-visible:ring-cyan-400"
              disabled={isImporting}
              onChange={(event) => void handleImportGcode(event.target.files?.[0])}
            />
          </label>
          {isImporting && (
            <p role="status" aria-label="Uploading G-code" className="border border-cyan-800 bg-cyan-950 text-cyan-100">
              Uploading G-code...
            </p>
          )}
          {importError && <p role="alert" className="border border-rose-800 bg-rose-950 text-rose-100">{importError}</p>}
          {artifact && missingPlanningValues.map((value) => (
            <Fragment key={value}>
              <p>{`${formatPlanningValueLabel(value)} is required.`}</p>
              <label>
                {formatPlanningValueLabel(value)}
                <input
                  className="border border-slate-700 bg-slate-800 text-slate-100 focus-visible:ring-2 focus-visible:ring-cyan-400"
                  value={planningValues[value] ?? ""}
                  onChange={(event) => setPlanningValues({ ...planningValues, [value]: event.target.value })}
                />
              </label>
            </Fragment>
          ))}
          {artifact && (
            <>
              <button
                type="button"
                className="border border-slate-700 bg-slate-800 text-slate-100 focus-visible:ring-2 focus-visible:ring-cyan-400"
                disabled={isImporting || hasBlankPlanningValue}
                onClick={() => void handleCreateJob()}
              >
                Create job
              </button>
              {isCreated && (
                <p role="status" aria-label="Job created" className="border border-emerald-800 bg-emerald-950 text-emerald-100">
                  Job created
                </p>
              )}
              {createError && <p role="alert" className="border border-rose-800 bg-rose-950 text-rose-100">{createError}</p>}
            </>
          )}
        </section>
        <section aria-labelledby="active-queue-heading" className="rounded-lg border border-slate-800 bg-slate-900 p-4">
          <h2 id="active-queue-heading">Active queue</h2>
          {jobs.map((job) => (
            <div key={job.id}>
              <div>{job.executionData.artifactRef === artifact?.id ? artifact.filename : job.executionData.artifactRef}</div>
              <div>{job.state}</div>
            </div>
          ))}
        </section>
        <aside aria-label="Backend runtime status" className="text-sm text-slate-400">
          <div>{`Backend app: ${appName}`}</div>
          <div>{`API base URL: ${apiBaseUrl}`}</div>
          <div>{`Backend status: ${status}`}</div>
        </aside>
      </div>
    </main>
  );
}
