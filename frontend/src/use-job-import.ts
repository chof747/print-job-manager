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
  const [extractedMetadata, setExtractedMetadata] = useState<Record<string, string | number>>({});
  const [provenance, setProvenance] = useState<Record<string, { parser: string; sourceKey: string }>>({});
  const [diagnostics, setDiagnostics] = useState<Array<{ code: string; sourceKey: string }>>([]);
  const [missingPlanningValues, setMissingPlanningValues] = useState<string[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [createError, setCreateError] = useState<string | null>(null);
  const [isCreated, setIsCreated] = useState(false);
  const [isImporting, setIsImporting] = useState(false);

  async function importFile(file: File | undefined) {
    if (!apiBaseUrl || !file) {
      return;
    }

    setIsImporting(true);
    try {
      const result = await importGcode(apiBaseUrl, file);
      setArtifact(result.artifact);
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
      await createJob(apiBaseUrl, artifactId, planningValues);
      jobCreated = true;
      setCreateError(null);
      const queue = await fetchQueue(apiBaseUrl);
      setJobs(queue.jobs);
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

  return { artifact, extractedMetadata, provenance, diagnostics, missingPlanningValues, jobs, createError, isCreated, isImporting, importFile, create };
}
