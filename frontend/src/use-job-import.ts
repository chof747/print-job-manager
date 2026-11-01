import { useEffect, useRef, useState } from "react";

import {
  createJob,
  fetchImportReview,
  fetchQueue,
  importGcode,
  type ImportedArtifact,
  type Job,
  type PlanningValues,
  updateJobScheduling,
} from "./job-import-api-client";

export function useJobImport(apiBaseUrl: string | null) {
  const [artifact, setArtifact] = useState<ImportedArtifact | null>(null);
  const [importId, setImportId] = useState<string | null>(null);
  const [extractedMetadata, setExtractedMetadata] = useState<Record<string, string | number>>({});
  const [provenance, setProvenance] = useState<Record<string, { parser: string; sourceKey: string }>>({});
  const [diagnostics, setDiagnostics] = useState<Array<{ code: string; sourceKey: string }>>([]);
  const [missingPlanningValues, setMissingPlanningValues] = useState<string[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [createError, setCreateError] = useState<string | null>(null);
  const [isCreated, setIsCreated] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const queueRequestVersion = useRef(0);

  useEffect(() => {
    if (!apiBaseUrl) {
      return;
    }

    const requestVersion = ++queueRequestVersion.current;
    void fetchQueue(apiBaseUrl)
      .then((queue) => {
        if (requestVersion === queueRequestVersion.current) {
          setJobs(queue.jobs);
        }
      })
      .catch(() => {});
  }, [apiBaseUrl]);

  async function importFile(file: File | undefined) {
    if (!apiBaseUrl || !file) {
      return;
    }

    setIsImporting(true);
    try {
      const uploaded = await importGcode(apiBaseUrl, file);
      const result = uploaded.import?.id
        ? await fetchImportReview(apiBaseUrl, uploaded.import.id)
        : uploaded;
      setArtifact(result.artifact);
      setImportId(uploaded.import?.id ?? null);
      setExtractedMetadata(result.extractedMetadata ?? {});
      setProvenance(result.provenance ?? {});
      setDiagnostics(result.diagnostics ?? []);
      setMissingPlanningValues(result.missingPlanningValues);
      setCreateError(null);
      setIsCreated(false);
    } finally {
      setIsImporting(false);
    }
  }

  async function create(artifactId: string, planningValues: PlanningValues) {
    if (!apiBaseUrl) {
      return;
    }

    let jobCreated = false;
    setIsCreated(false);
    try {
      await createJob(apiBaseUrl, importId ?? artifactId, planningValues);
      jobCreated = true;
      setCreateError(null);
      const requestVersion = ++queueRequestVersion.current;
      const queue = await fetchQueue(apiBaseUrl);
      if (requestVersion === queueRequestVersion.current) {
        setJobs((currentJobs) => queue.jobs.map((queuedJob) => {
          const currentJob = currentJobs.find((item) => item.id === queuedJob.id);
          return currentJob && currentJob.version > queuedJob.version ? currentJob : queuedJob;
        }));
      }
      setIsCreated(true);
    } catch (error: unknown) {
      if (jobCreated) {
        setCreateError("Job was created, but the active queue could not be refreshed");
        return;
      }

      const detail = error && typeof error === "object" && "detail" in error ? error.detail : undefined;
      const missingValues =
        detail &&
        typeof detail === "object" &&
        "missingPlanningValues" in detail &&
        Array.isArray(detail.missingPlanningValues)
          ? detail.missingPlanningValues
          : null;
      setCreateError(
        missingValues
          ? `Missing planning values: ${missingValues.join(", ")}`
          : typeof detail === "string"
            ? detail
            : "Unable to create job",
      );
    }
  }

  async function updateScheduling(job: Job, changes: { priority?: number; dueDate?: string | null; notes?: string | null; tags?: string[]; printerAssignment?: { mode: "preferred" | "required"; printerId: string } | null }) {
    if (!apiBaseUrl) {
      return;
    }

    const updatedJob = await updateJobScheduling(apiBaseUrl, job.id, {
      ...changes,
      expectedVersion: job.version,
    });
    setJobs((currentJobs) => currentJobs.map((currentJob) => currentJob.id === updatedJob.id ? updatedJob : currentJob));
    return updatedJob;
  }

  return { artifact, extractedMetadata, provenance, diagnostics, missingPlanningValues, jobs, createError, isCreated, isImporting, importFile, create, updateScheduling };
}
