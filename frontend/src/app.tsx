import { Fragment, useContext, useEffect, useRef, useState } from "react";

import { fetchBackendConfig, fetchBackendHealth } from "./backend-health";
import { loadRuntimeConfig } from "./runtime-config";
import { BootstrapStateCacheContext, RuntimeConfigContext } from "./runtime-config-gate";
import { Badge, Button, Card, FormField, ReasonList, StatusPill, Stepper } from "./ui";
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
    <main aria-label="Operations" className="min-h-screen bg-slate-50 text-slate-900">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/90 px-4 py-4 backdrop-blur md:px-6">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight">Print Job Manager</h1>
            <p className="text-sm text-slate-500">Structured operations shell</p>
          </div>
          <Badge className="bg-indigo-50 text-indigo-800">Operations</Badge>
        </div>
      </header>
      <div className="mx-auto grid max-w-7xl grid-cols-1 gap-5 p-4 md:p-6 lg:grid-cols-[minmax(0,1fr)_300px]">
        <Card aria-labelledby="guided-import-heading" className="border-indigo-200 bg-gradient-to-br from-indigo-50 to-white">
          <div className="mb-5 flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-extrabold uppercase tracking-widest text-indigo-700">Import G-code</p>
              <h2 id="guided-import-heading" className="mt-1 text-2xl font-bold tracking-tight">Guided import</h2>
              <p className="mt-1 text-sm text-slate-600">Create a complete job from one uploaded G-code file.</p>
            </div>
            <StatusPill tone={artifact ? "ready" : "neutral"}>{artifact ? "Uploaded" : "Awaiting file"}</StatusPill>
          </div>
          <Stepper activeStep={artifact ? 2 : 0} />
          <div className="mt-6 grid gap-4">
            <FormField label="G-code file">
            <input
              type="file"
              accept=".gcode"
              aria-label="G-code file"
              className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
              disabled={isImporting}
              onChange={(event) => void handleImportGcode(event.target.files?.[0])}
            />
            </FormField>
          {isImporting && (
            <p role="status" aria-label="Uploading G-code" className="rounded-xl border border-indigo-200 bg-indigo-100 px-3 py-2 text-sm font-bold text-indigo-800">
              Uploading G-code...
            </p>
          )}
          {importError && <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">{importError}</p>}
          {artifact && missingPlanningValues.map((value) => (
            <Fragment key={value}>
              <p className="text-sm text-slate-600">{`${formatPlanningValueLabel(value)} is required.`}</p>
              <FormField label={formatPlanningValueLabel(value)}>
                <input
                  className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
                  value={planningValues[value] ?? ""}
                  onChange={(event) => setPlanningValues({ ...planningValues, [value]: event.target.value })}
                />
              </FormField>
            </Fragment>
          ))}
          {artifact && (
            <>
              <ReasonList reasons={missingPlanningValues.length ? ["Complete the required planning values before creating the job."] : ["This job has all required planning values."]} />
              <Button
                type="button"
                disabled={isImporting || hasBlankPlanningValue}
                onClick={() => void handleCreateJob()}
              >
                Create job
              </Button>
              {isCreated && (
                <p role="status" aria-label="Job created" className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-bold text-emerald-800">
                  Job created
                </p>
              )}
              {createError && <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">{createError}</p>}
            </>
          )}
          </div>
        </Card>
        <Card as="aside" aria-label="Backend runtime status" className="h-fit">
          <p className="text-xs font-extrabold uppercase tracking-widest text-slate-500">System summary</p>
          <h2 className="mt-1 text-lg font-bold">Backend runtime</h2>
          <dl className="mt-4 grid gap-3 text-sm">
            <div><dt className="text-slate-500">Backend app</dt><dd className="font-bold">{appName}</dd></div>
            <div><dt className="text-slate-500">API base URL</dt><dd className="break-all font-bold">{apiBaseUrl}</dd></div>
            <div className="flex items-center justify-between gap-3"><dt className="text-slate-500">Backend status</dt><dd><StatusPill tone={status === "ok" ? "ready" : "attention"}>{status}</StatusPill></dd></div>
          </dl>
        </Card>
        <Card aria-labelledby="active-queue-heading" className="lg:col-span-2">
          <h2 id="active-queue-heading">Active queue</h2>
          <p className="mt-1 text-sm text-slate-500">The queue is the scheduler's projection of active jobs.</p>
          <div className="mt-4 grid gap-2">
            {jobs.map((job) => (
              <div key={job.id} className="flex items-center justify-between gap-4 rounded-xl border border-slate-200 px-4 py-3">
                <strong>{job.executionData.artifactRef === artifact?.id ? artifact.filename : job.executionData.artifactRef}</strong>
                <StatusPill tone="ready">{job.state}</StatusPill>
              </div>
            ))}
            {!jobs.length && <p className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-500">No active jobs yet.</p>}
          </div>
        </Card>
      </div>
    </main>
  );
}
