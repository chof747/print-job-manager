import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";

import type { UpdateSchedulingRequest } from "./generated/scheduling/models/UpdateSchedulingRequest";
import {
  createJob,
  fetchCockpit,
  fetchImportReview,
  fetchQueue,
  importGcode,
  type Cockpit,
  type ImportedArtifact,
  type Job,
  type PlanningValues,
} from "./job-import-api-client";
import { useJobScheduling } from "./use-job-scheduling";

export function useJobImport(apiBaseUrl: string | null, materialFilter = "") {
  const [artifact, setArtifact] = useState<ImportedArtifact | null>(null);
  const [importId, setImportId] = useState<string | null>(null);
  const [extractedMetadata, setExtractedMetadata] = useState<Record<string, string | number>>({});
  const [provenance, setProvenance] = useState<Record<string, { parser: string; sourceKey: string }>>({});
  const [diagnostics, setDiagnostics] = useState<Array<{ code: string; sourceKey: string }>>([]);
  const [missingPlanningValues, setMissingPlanningValues] = useState<string[]>([]);
  const queryClient = useQueryClient();
  const queueKey = ["active-queue", apiBaseUrl];
  const cockpitKey = ["cockpit", apiBaseUrl, materialFilter];
  const { data: cockpit, isError: cockpitError } = useQuery({
    queryKey: cockpitKey,
    queryFn: () => fetchCockpit(apiBaseUrl!, materialFilter),
    enabled: apiBaseUrl !== null,
    retry: false,
  });
  const { data: jobs = [] } = useQuery<Job[]>({
    queryKey: queueKey,
    queryFn: async () => (await fetchQueue(apiBaseUrl!)).jobs,
    enabled: apiBaseUrl !== null,
    retry: false,
    staleTime: Infinity,
    structuralSharing: (oldData, newData) => {
      const currentJobs = oldData as Job[] | undefined;
      return (newData as Job[]).map((queuedJob) => {
        const currentJob = currentJobs?.find((item) => item.id === queuedJob.id);
        return currentJob && currentJob.version > queuedJob.version ? currentJob : queuedJob;
      });
    },
  });
  const [createError, setCreateError] = useState<string | null>(null);
  const [isCreated, setIsCreated] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const queueRequestVersion = useRef(0);
  const schedulingMutation = useJobScheduling();

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
      const createdJob = await createJob(apiBaseUrl, importId ?? artifactId, planningValues);
      jobCreated = true;
      setCreateError(null);
      void queryClient.invalidateQueries({ queryKey: ["cockpit", apiBaseUrl] });
      const requestVersion = ++queueRequestVersion.current;
      await queryClient.cancelQueries({ queryKey: queueKey, exact: true });
      const queue = await fetchQueue(apiBaseUrl);
      if (requestVersion === queueRequestVersion.current) {
        queryClient.setQueryData<Job[]>(queueKey, (currentJobs = []) => queue.jobs.map((queuedJob) => {
          const currentJob = currentJobs.find((item) => item.id === queuedJob.id);
          return currentJob && currentJob.version > queuedJob.version ? currentJob : queuedJob;
        }));
      }
      queryClient.setQueryData<Cockpit>(cockpitKey, (current) => {
        if (!current || materialFilter || current.activeJobs.some((job) => job.id === createdJob.id)) return current;
        return { ...current, activeJobs: [...current.activeJobs, createdJob] };
      });
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

  async function updateScheduling(job: Job, changes: Omit<UpdateSchedulingRequest, "expectedVersion">) {
    if (!apiBaseUrl) {
      return;
    }

    const updatedJob = await schedulingMutation.mutateAsync({
      apiBaseUrl,
      jobId: job.id,
      changes: { ...changes, expectedVersion: job.version },
    });
    queryClient.setQueryData<Job[]>(queueKey, (currentJobs = []) => currentJobs.map((currentJob) =>
      currentJob.id === updatedJob.id && currentJob.version <= updatedJob.version ? updatedJob : currentJob,
    ));
    void queryClient.invalidateQueries({ queryKey: ["cockpit", apiBaseUrl] });
    return updatedJob;
  }

  return { artifact, extractedMetadata, provenance, diagnostics, missingPlanningValues, jobs, cockpit, cockpitError, createError, isCreated, isImporting, importFile, create, updateScheduling };
}
