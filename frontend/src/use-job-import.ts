import { useState } from "react";

import {
  createJob,
  fetchQueue,
  importGcode,
  type ImportedArtifact,
  type Job,
  type PlanningValues,
} from "./job-import-api-client";

export function useJobImport(apiBaseUrl: string | null) {
  const [artifact, setArtifact] = useState<ImportedArtifact | null>(null);
  const [missingPlanningValues, setMissingPlanningValues] = useState<string[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [createError, setCreateError] = useState<string | null>(null);
  const [isImporting, setIsImporting] = useState(false);

  async function importFile(file: File | undefined) {
    if (!apiBaseUrl || !file) {
      return;
    }

    setIsImporting(true);
    try {
      const result = await importGcode(apiBaseUrl, file);
      setArtifact(result.artifact);
      setMissingPlanningValues(result.missingPlanningValues);
      setCreateError(null);
    } finally {
      setIsImporting(false);
    }
  }

  async function create(artifactId: string, planningValues: PlanningValues) {
    if (!apiBaseUrl) {
      return;
    }

    let jobCreated = false;
    try {
      await createJob(apiBaseUrl, artifactId, planningValues);
      jobCreated = true;
      setCreateError(null);
      const queue = await fetchQueue(apiBaseUrl);
      setJobs(queue.jobs);
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

  return { artifact, missingPlanningValues, jobs, createError, isImporting, importFile, create };
}
