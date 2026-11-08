import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { Fragment, useContext, useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";

import { fetchBackendConfig, fetchBackendHealth } from "./backend-health";
import type { Job } from "./job-import-api-client";
import { fetchJob } from "./job-import-api-client";
import { loadRuntimeConfig } from "./runtime-config";
import { BootstrapStateCacheContext, RuntimeConfigContext } from "./runtime-config-gate";
import { Badge, Button, Card, FormField, ReasonList, StatusPill, Stepper } from "./ui";
import { useJobImport } from "./use-job-import";
import { QueueFilters } from "./queue-filters";
import { OperatorSetup, SetupDialog } from "./operator-setup";
import { useJobEligibility } from "./use-job-eligibility";
import type { EligibilityResponse } from "./generated/scheduling/models/EligibilityResponse";


function formatEstimatedDuration(seconds: number) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = seconds % 60;

  return hours ? `${hours}h ${minutes}m ${remainingSeconds}s` : `${minutes}m ${remainingSeconds}s`;
}

function formatTags(tags: string[]) {
  return tags.map((tag) =>
    !tag || /[",\r\n]/.test(tag) || tag !== tag.trim()
      ? `"${tag.replace(/"/g, '""')}"`
      : tag,
  ).join(", ");
}

function parseTags(input: string): string[] {
  const tags: string[] = [];
  let index = 0;
  while (index < input.length) {
    while (index < input.length && /\s/.test(input[index])) index++;
    let tag = "";
    if (input[index] === '"') {
      index++;
      let closed = false;
      while (index < input.length) {
        if (input[index] === '"') {
          if (input[index + 1] === '"') {
            tag += '"';
            index += 2;
          } else {
            index++;
            closed = true;
            break;
          }
        } else {
          tag += input[index++];
        }
      }
      while (index < input.length && /\s/.test(input[index])) index++;
      if (!closed || (index < input.length && input[index] !== ",")) {
        throw new Error("Invalid quoted tag");
      }
      tags.push(tag);
    } else {
      while (index < input.length && input[index] !== ",") {
        if (input[index] === '"') throw new Error("Invalid quoted tag");
        tag += input[index++];
      }
      if (tag.trim()) tags.push(tag.trim());
    }
    if (input[index] === ",") index++;
  }
  return tags;
}

type SchedulingFormValues = {
  priority: string;
  dueDate: string;
  notes: string;
  tags: string;
  assignmentMode: "" | "preferred" | "required";
  printerId: string;
};

type ImportFormValues = {
  planningValues: Record<string, string>;
  requireEnclosure: boolean;
  requireHardenedNozzle: boolean;
  materialColor: string;
  materialAmount: string;
  requiredVolume: { x: string; y: string; z: string };
};

function formatExtractedValue(key: string, value: unknown) {
  if (key === "estimatedDuration" && typeof value === "number") return formatEstimatedDuration(value);
  if (key === "dimensions" && value && typeof value === "object" && "x" in value && "y" in value && "z" in value) {
    return `${value.x} × ${value.y} × ${value.z} mm`;
  }
  return String(value);
}


export function App() {
  const [queryClient] = useState(() => new QueryClient());
  return <QueryClientProvider client={queryClient}><AppContent /></QueryClientProvider>;
}

function jobFilename(executionData: unknown, artifact: { id: string; filename: string } | null) {
  if (executionData && typeof executionData === "object") {
    if ("artifactFilename" in executionData && typeof executionData.artifactFilename === "string") {
      return executionData.artifactFilename;
    }
    if (artifact && "artifactRef" in executionData && executionData.artifactRef === artifact.id) {
      return artifact.filename;
    }
  }
  return "Legacy G-code job";
}

function AppContent() {
  const runtimeConfig = useContext(RuntimeConfigContext);
  const bootstrapStateCache = useContext(BootstrapStateCacheContext);
  const hasBootstrappedSuccessfully = useRef(false);
  const [status, setStatus] = useState<string | null>(bootstrapStateCache?.value?.status ?? null);
  const [appName, setAppName] = useState<string | null>(bootstrapStateCache?.value?.appName ?? null);
  const [apiBaseUrl, setApiBaseUrl] = useState<string | null>(bootstrapStateCache?.value?.apiBaseUrl ?? null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [requirementErrors, setRequirementErrors] = useState<string[]>([]);
  const importForm = useForm<ImportFormValues>({
    defaultValues: { planningValues: {}, requireEnclosure: false, requireHardenedNozzle: false, materialColor: "", materialAmount: "", requiredVolume: { x: "", y: "", z: "" } },
  });
  const planningValues = importForm.watch("planningValues");
  const [editingJob, setEditingJob] = useState<Job | null>(null);
  const [detailJob, setDetailJob] = useState<Job | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [eligibilityPrinterId, setEligibilityPrinterId] = useState("");
  const [eligibility, setEligibility] = useState<({ printerId: string } & EligibilityResponse) | null>(null);
  const [eligibilityError, setEligibilityError] = useState<string | null>(null);
  const eligibilityRequest = useRef(0);
  const eligibilityMutation = useJobEligibility();
  const printers = useQuery({
    queryKey: ["printers", apiBaseUrl],
    enabled: !!apiBaseUrl,
    queryFn: async (): Promise<string[]> => {
      const response = await fetch(`${apiBaseUrl}/printers`);
      if (!response.ok) throw new Error("Unable to load printers");
      return response.json();
    },
  });
  const [detailSelection, setDetailSelection] = useState<{ jobId: string; section: string } | null>(null);
  const detailRequest = useRef(0);
  const [materialFilter, setMaterialFilter] = useState("");
  const editingSession = useRef(0);
  const [schedulingError, setSchedulingError] = useState<string | null>(null);
  const { register, reset, getValues, watch } = useForm<SchedulingFormValues>({
    defaultValues: { priority: "", dueDate: "", notes: "", tags: "", assignmentMode: "", printerId: "" },
  });
  const assignmentMode = watch("assignmentMode");
  const { artifact, extractedMetadata, provenance, diagnostics, missingPlanningValues, jobs, cockpit, cockpitError, createError, isCreated, isImporting, importFile, create, updateScheduling } = useJobImport(apiBaseUrl, materialFilter);

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
      setRequirementErrors([]);
      importForm.reset({
        planningValues: Object.fromEntries(Object.keys(importForm.getValues("planningValues")).map((key) => [key, ""])),
        requireEnclosure: false, requireHardenedNozzle: false, materialColor: "", materialAmount: "",
        requiredVolume: { x: "", y: "", z: "" },
      });
    } catch (error: unknown) {
      setImportError(error instanceof Error ? error.message : "Unable to import G-code");
    }
  }

  async function handleCreateJob() {
    const { planningValues, requireEnclosure, requireHardenedNozzle, materialColor, materialAmount, requiredVolume } = importForm.getValues();
    if (!artifact || missingPlanningValues.some((value) => !planningValues[value]?.trim())) {
      return;
    }
    const nozzle = planningValues.nozzleDiameter;
    const errors: string[] = [];
    if (nozzle && (!Number.isFinite(Number(nozzle)) || Number(nozzle) <= 0)) errors.push("Enter a positive finite nozzle diameter.");
    const hasMaterialRequirement = Boolean(materialColor.trim() || materialAmount.trim());
    if (materialAmount.trim() && (!Number.isFinite(Number(materialAmount)) || Number(materialAmount) <= 0)) errors.push("Enter a positive finite material amount.");
    const volumeValues = [requiredVolume.x, requiredVolume.y, requiredVolume.z];
    const hasVolumeRequirement = volumeValues.some((value) => value.trim());
    if (hasVolumeRequirement && volumeValues.some((value) => !value.trim() || !Number.isFinite(Number(value)) || Number(value) <= 0)) errors.push("Enter positive finite values for all three build volume dimensions (X, Y, and Z).");
    setRequirementErrors(errors);
    if (errors.length) return;
    const requirements = {
      ...(requireEnclosure ? { enclosure: true } : {}),
      ...(requireHardenedNozzle ? { hardenedNozzle: true } : {}),
      ...(hasMaterialRequirement ? { material: { ...(materialColor.trim() ? { color: materialColor.trim() } : {}), ...(materialAmount.trim() ? { amountGrams: Number(materialAmount) } : {}) } } : {}),
      ...(hasVolumeRequirement ? { buildVolume: { x: Number(requiredVolume.x), y: Number(requiredVolume.y), z: Number(requiredVolume.z) } } : {}),
    };
    const submittedValues = Object.fromEntries(Object.entries(planningValues).filter(([, value]) => value.trim()));
    if (!submittedValues.nozzleDiameter?.trim()) delete submittedValues.nozzleDiameter;
    await create(artifact.id, submittedValues, Object.keys(requirements).length ? requirements : undefined);
  }

  async function handleJobDetails(jobId: string, section: string) {
    const request = ++detailRequest.current;
    eligibilityRequest.current++;
    setEligibilityPrinterId("");
    setEligibility(null);
    setEligibilityError(null);
    setDetailSelection({ jobId, section });
    setDetailJob(null);
    setDetailError(null);
    try {
      const job = await fetchJob(apiBaseUrl!, jobId);
      if (detailRequest.current === request) {
        setDetailJob(job);
        setEligibilityPrinterId(job.schedulingData.printerAssignment?.printerId ?? "");
      }
    } catch {
      if (detailRequest.current === request) setDetailError("Unable to fetch job details");
    }
  }

  async function handleCheckEligibility(jobId: string) {
    const printerId = eligibilityPrinterId.trim();
    if (!printerId) {
      setEligibilityError("Select a printer to check eligibility.");
      return;
    }
    const request = ++eligibilityRequest.current;
    setEligibility(null);
    setEligibilityError(null);
    try {
      const result = await eligibilityMutation.mutateAsync({ apiBaseUrl: apiBaseUrl!, jobId, printerId });
      if (eligibilityRequest.current === request) setEligibility({ printerId, ...result });
    } catch {
      if (eligibilityRequest.current === request) setEligibilityError("Unable to check eligibility");
    }
  }

  function renderJobDetails(jobId: string, section: string) {
    if (detailSelection?.jobId !== jobId || detailSelection.section !== section) return null;
    return (
      <Card aria-label="Job details" className="mt-3 bg-slate-50">
        <div className="flex items-center justify-between gap-4">
          <h3 className="text-base font-bold text-slate-900">Job details</h3>
          <button type="button" aria-label="Close details" className="rounded-md p-1 text-slate-500 hover:bg-slate-200 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400" onClick={() => {
            detailRequest.current++;
            eligibilityRequest.current++;
            setDetailSelection(null);
            setDetailJob(null);
            setDetailError(null);
          }}>
            <svg aria-hidden="true" className="h-5 w-5" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M5 5l10 10M15 5L5 15" />
            </svg>
          </button>
        </div>
        {detailError ? <p role="alert">{detailError}</p> : detailJob ? (
          <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
            <div><dt className="text-slate-500">File</dt><dd className="mt-1 break-all font-medium text-slate-900">{jobFilename(detailJob.executionData, artifact)}</dd></div>
            <div><dt className="text-slate-500">Status</dt><dd className="mt-1 font-medium text-slate-900">{detailJob.state}</dd></div>
            {typeof detailJob.executionData.material === "string" && <div><dt className="text-slate-500">Material</dt><dd className="mt-1 font-medium text-slate-900">{detailJob.executionData.material}</dd></div>}
          </dl>
        ) : <p role="status">Loading job details…</p>}
        {detailJob && section === "active" && (
          <div>
            <FormField label="Printer ID">
              <select aria-invalid={eligibilityError === "Select a printer to check eligibility." || undefined} aria-describedby={eligibilityError === "Select a printer to check eligibility." ? "eligibility-printer-error" : undefined} className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400" value={eligibilityPrinterId} onChange={(event) => {
                eligibilityRequest.current++;
                setEligibilityPrinterId(event.target.value);
                setEligibility(null);
                setEligibilityError(null);
              }}>
                <option value="">Select a printer</option>
                {eligibilityPrinterId && !printers.data?.includes(eligibilityPrinterId) && <option value={eligibilityPrinterId}>{eligibilityPrinterId}{printers.isSuccess ? " (not in printer catalog)" : ""}</option>}
                {(printers.data ?? []).map((id) => <option key={id} value={id}>{id}</option>)}
              </select>
            </FormField>
            {eligibilityError === "Select a printer to check eligibility." && <p id="eligibility-printer-error" role="alert" className="mt-2 rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">{eligibilityError}</p>}
            {printers.isLoading && <p role="status">Loading printers…</p>}
            {printers.isError && <p role="alert">Unable to load printers. Try refreshing the page.</p>}
            {printers.isSuccess && printers.data.length === 0 && <p>No printers available. Set up a printer first.</p>}
            <Button type="button" onClick={() => void handleCheckEligibility(jobId)}>Check eligibility</Button>
            {eligibilityError && eligibilityError !== "Select a printer to check eligibility." && <SetupDialog title="Eligibility check failed" onClose={() => setEligibilityError(null)}>
              <p role="alert" className="rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">{eligibilityError}. Please try again.</p>
            </SetupDialog>}
            {eligibility && !eligibility.eligible && <SetupDialog title="Job blocked" onClose={() => setEligibility(null)}>
              <div role="alert" className="rounded-xl border border-red-300 bg-red-50 p-4 text-red-800">
                <p className="font-bold">{eligibility.printerId}: Blocked</p>
                <p className="mt-2 text-sm">This job cannot run on this printer because:</p>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">{eligibility.failures.map((failure, index) => <li key={`${failure.code}-${index}`}>{failure.code.replace(/_/g, " ")}</li>)}</ul>
              </div>
              {!!eligibility.satisfied?.length && <div className="mt-4 text-sm text-slate-600"><p className="font-bold">Satisfied requirements</p><ul className="mt-2 list-disc pl-5">{eligibility.satisfied.map((item, index) => <li key={`${item.code}-${index}`}>{item.code.replace(/_/g, " ")}</li>)}</ul></div>}
            </SetupDialog>}
            {eligibility?.eligible && <SetupDialog title="Job eligible" onClose={() => setEligibility(null)}>
              <div role="status" className="rounded-xl border border-emerald-300 bg-emerald-50 p-4 text-emerald-800">
                <p className="font-bold">{eligibility.printerId}: Eligible</p>
                <p className="mt-2 text-sm">This job can run on this printer based on the current eligibility checks.</p>
                {!!eligibility.satisfied?.length && <><p className="mt-3 text-sm font-bold">Satisfied requirements</p><ul className="mt-2 list-disc space-y-1 pl-5 text-sm">{eligibility.satisfied.map((item, index) => <li key={`${item.code}-${index}`}>{item.code.replace(/_/g, " ")}</li>)}</ul></>}
              </div>
            </SetupDialog>}
          </div>
        )}
      </Card>
    );
  }

  async function handleSaveScheduling(job: (typeof jobs)[number]) {
    const session = editingSession.current;
    const { priority, dueDate, notes, tags, assignmentMode, printerId } = getValues();
    const printerAssignment = assignmentMode ? { mode: assignmentMode, printerId } : null;
    setSchedulingError(null);
    if (!priority.trim()) {
      setSchedulingError("Priority is required");
      return;
    }
    if (assignmentMode && !printers.data?.includes(printerId)) {
      setSchedulingError("Select a registered printer for this assignment.");
      return;
    }
    try {
      const parsedTags = parseTags(tags);
      const updatedJob = await updateScheduling(job, {
      ...(Number(priority) !== job.schedulingData.priority ? { priority: Number(priority) } : {}),
      ...(dueDate !== (job.schedulingData.dueDate ?? "") ? { dueDate: dueDate || null } : {}),
      ...(notes !== (job.schedulingData.notes ?? "") ? { notes } : {}),
      ...(tags !== formatTags(job.schedulingData.tags ?? []) ? { tags: parsedTags } : {}),
      ...(JSON.stringify(printerAssignment) !== JSON.stringify(job.schedulingData.printerAssignment ?? null) ? { printerAssignment } : {}),
      });
      if (updatedJob && editingSession.current === session) {
        setEditingJob((currentJob) => currentJob?.id === job.id ? updatedJob : currentJob);
      }
    } catch (error: unknown) {
      if (editingSession.current === session) {
        setSchedulingError(error instanceof Error ? error.message : "Unable to update job scheduling");
      }
    }
  }

  const formatPlanningValueLabel = (value: string) => value.replace(/([a-z])([A-Z])/g, "$1 $2");
  const hasBlankPlanningValue = missingPlanningValues.some((value) => !planningValues[value]?.trim());
  const activeJobs = cockpit ? cockpit.activeJobs.map((job) => {
    const queuedJob = jobs.find((item) => item.id === job.id);
    return queuedJob && queuedJob.version > job.version ? queuedJob : job;
  }) : materialFilter ? [] : jobs;

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
        {cockpitError && <p role="alert">Unable to load cockpit</p>}
        <Card aria-labelledby="active-queue-heading" className="lg:col-span-2">
          <h2 id="active-queue-heading">Active queue</h2>
          <QueueFilters applied={materialFilter} onApply={setMaterialFilter} />
          <p className="mt-1 text-sm text-slate-500">The queue is the scheduler's projection of active jobs.</p>
          <div className="mt-4 grid gap-2">
            {activeJobs.map((job) => (
              <div key={job.id} className="rounded-xl border border-slate-200 px-4 py-3">
                <div className="flex items-center justify-between gap-4">
                  <strong>{jobFilename(job.executionData, artifact)}</strong>
                  <StatusPill tone="ready">{job.state}</StatusPill>
                </div>
                <p className="mt-1 text-sm text-slate-500">Priority: {job.schedulingData.priority}</p>
                {job.schedulingData.dueDate && <p>Due date: {job.schedulingData.dueDate}</p>}
                {typeof job.executionData.material === "string" && <p>Material: {job.executionData.material}</p>}
                {job.schedulingData.printerAssignment && (
                  <p>Printer: {job.schedulingData.printerAssignment.mode} {job.schedulingData.printerAssignment.printerId}</p>
                )}
                <Button type="button" onClick={() => void handleJobDetails(job.id, "active")}>Details</Button>
                {renderJobDetails(job.id, "active")}
                {job.state === "ready" && (
                  editingJob?.id === job.id ? (
                    <div className="mt-3 flex items-end gap-3">
                      <FormField label="Priority">
                        <input
                          type="number"
                          className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
                          {...register("priority")}
                        />
                      </FormField>
                      <FormField label="Due date">
                        <input
                          type="date"
                          className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
                          {...register("dueDate")}
                        />
                      </FormField>
                      <FormField label="Notes">
                        <textarea
                          className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
                          {...register("notes")}
                        />
                      </FormField>
                      <FormField label="Tags">
                        <input
                          className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
                          {...register("tags")}
                        />
                      </FormField>
                      <FormField label="Assignment mode">
                        <select className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400" {...register("assignmentMode")}>
                          <option value="">None</option>
                          <option value="preferred">Preferred</option>
                          <option value="required">Required</option>
                        </select>
                      </FormField>
                      {assignmentMode !== "" && (
                        <FormField label="Printer ID">
                          <select className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400" {...register("printerId")}>
                            <option value="">Select a printer</option>
                            {(printers.data ?? []).map((id) => <option key={id} value={id}>{id}</option>)}
                          </select>
                        </FormField>
                      )}
                      {assignmentMode !== "" && printers.isError && <p role="alert">Unable to load printers. Try refreshing the page.</p>}
                      {assignmentMode !== "" && printers.isSuccess && printers.data.length === 0 && <p>No printers available. Set up a printer first.</p>}
                      {schedulingError && <p role="alert">{schedulingError}</p>}
                      <Button type="button" onClick={() => void handleSaveScheduling(editingJob)}>Save scheduling</Button>
                    </div>
                  ) : (
                    <Button
                      type="button"
                      variant="secondary"
                      className="mt-3"
                      onClick={() => {
                        editingSession.current++;
                        setEditingJob(job);
                        setSchedulingError(null);
                        reset({
                          priority: String(job.schedulingData.priority),
                          dueDate: job.schedulingData.dueDate ?? "",
                          notes: job.schedulingData.notes ?? "",
                          tags: formatTags(job.schedulingData.tags ?? []),
                          assignmentMode: job.schedulingData.printerAssignment?.mode ?? "",
                          printerId: job.schedulingData.printerAssignment?.printerId ?? "",
                        });
                      }}
                    >
                      Edit scheduling
                    </Button>
                  )
                )}
              </div>
            ))}
            {!activeJobs.length && <p className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-500">No active jobs yet.</p>}
          </div>
        </Card>
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
            {artifact && Object.entries(extractedMetadata).map(([key, value]) => (
             <Fragment key={key}>
               <FormField label={formatPlanningValueLabel(key)}>
                 <input
                    className="rounded-xl border border-slate-300 bg-slate-100 px-3 py-2 text-slate-900 shadow-sm"
                    readOnly
                    value={formatExtractedValue(key, value)}
                  />
               </FormField>
                {provenance[key] && <p className="text-sm text-slate-500">Source: {provenance[key].parser}, {provenance[key].sourceKey}</p>}
              </Fragment>
            ))}
           {artifact && diagnostics.map((diagnostic) => (
             <p key={`${diagnostic.code}-${diagnostic.sourceKey}`} className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
               {`${diagnostic.code.replace(/_/g, " ").replace(/^./, (letter) => letter.toUpperCase())}: ${diagnostic.sourceKey}`}
             </p>
           ))}
           {artifact && missingPlanningValues.map((value) => (
            <Fragment key={value}>
              <p className="text-sm text-slate-600">{`${formatPlanningValueLabel(value)} is required.`}</p>
              <FormField label={formatPlanningValueLabel(value)}>
                <input
                  className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
                  {...importForm.register(`planningValues.${value}`)}
                />
              </FormField>
            </Fragment>
           ))}
           {artifact && extractedMetadata.nozzleDiameter == null && !missingPlanningValues.includes("nozzleDiameter") && (
             <FormField label="Nozzle diameter">
               <input type="number" min="0" step="any" {...importForm.register("planningValues.nozzleDiameter")} />
             </FormField>
           )}
           {artifact && (
             <>
              <label>
                 <input type="checkbox" {...importForm.register("requireEnclosure")} />
                Require enclosure
              </label>
              <label>
                 <input type="checkbox" {...importForm.register("requireHardenedNozzle")} />
                Require hardened nozzle
              </label>
              <FormField label="Material color">
                 <input {...importForm.register("materialColor")} />
              </FormField>
              <FormField label="Material amount (grams)">
                 <input type="number" min="0" {...importForm.register("materialAmount")} />
              </FormField>
              {(["x", "y", "z"] as const).map((axis) => (
                <FormField key={axis} label={`Minimum build volume ${axis.toUpperCase()}`}>
                  <input type="number" min="0" step="any" {...importForm.register(`requiredVolume.${axis}`)} />
                </FormField>
              ))}
              {requirementErrors.length > 0 && <div role="alert">{requirementErrors.map((error) => <p key={error}>{error}</p>)}</div>}
              {(missingPlanningValues.length > 0 || requirementErrors.length === 0) && <ReasonList reasons={missingPlanningValues.length ? ["Complete the required planning values before creating the job."] : ["This job has all required planning values."]} />}
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
        <OperatorSetup apiBaseUrl={apiBaseUrl} />
        <Card as="aside" aria-label="Backend runtime status" className="h-fit">
          <p className="text-xs font-extrabold uppercase tracking-widest text-slate-500">System summary</p>
          <h2 className="mt-1 text-lg font-bold">Backend runtime</h2>
          <dl className="mt-4 grid gap-3 text-sm">
            <div><dt className="text-slate-500">Backend app</dt><dd className="font-bold">{appName}</dd></div>
            <div><dt className="text-slate-500">API base URL</dt><dd className="break-all font-bold">{apiBaseUrl}</dd></div>
            <div className="flex items-center justify-between gap-3"><dt className="text-slate-500">Backend status</dt><dd><StatusPill tone={status === "ok" ? "ready" : "attention"}>{status}</StatusPill></dd></div>
          </dl>
        </Card>
        <Card aria-label="Failures">
          <h2>Failures</h2>
          {cockpit?.failures.map((job) => (
            <div key={job.id}>
              <p>{jobFilename(job.executionData, artifact)}</p>
              <Button type="button" onClick={() => void handleJobDetails(job.id, "failures")}>Details</Button>
              {renderJobDetails(job.id, "failures")}
            </div>
          ))}
        </Card>
        <Card aria-label="Recent history">
          <h2>Recent history</h2>
          {cockpit?.recentHistory.map((job) => (
            <div key={job.id}>
              <p>{jobFilename(job.executionData, artifact)} — {job.state}</p>
              <Button type="button" onClick={() => void handleJobDetails(job.id, "history")}>Details</Button>
              {renderJobDetails(job.id, "history")}
            </div>
          ))}
        </Card>
      </div>
    </main>
  );
}
