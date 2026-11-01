import { ApiError } from "./generated/scheduling/core/ApiError";
import { SchedulingClient } from "./generated/scheduling/SchedulingClient";

export type ImportedArtifact = {
  id: string;
  filename: string;
};

export type ImportGcodeResult = {
  artifact: ImportedArtifact;
  extractedMetadata?: Record<string, string | number>;
  provenance?: Record<string, { parser: string; sourceKey: string }>;
  diagnostics?: Array<{ code: string; sourceKey: string }>;
  missingPlanningValues: string[];
};

export type Job = {
  id: string;
  state: string;
  version: number;
  executionData: {
    artifactRef: string;
    artifactFilename?: string;
  };
  schedulingData: {
    priority: number;
    dueDate?: string | null;
    notes?: string | null;
    tags?: string[];
    printerAssignment?: { mode: "preferred" | "required"; printerId: string } | null;
  };
};

export type Queue = {
  jobs: Job[];
};

export type CreateJobError = Error & {
  detail?: unknown;
};

export type PlanningValues = Record<string, string>;

export type ImportGcodeRequest = {
  file: File;
};

export type CreateJobRequest = {
  artifactId: string;
  planningValues: PlanningValues;
};

export async function importGcode(apiBaseUrl: string, file: File): Promise<ImportGcodeResult> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${apiBaseUrl}/import`, { method: "POST", body: formData });

  if (!response.ok) {
    throw new Error("Unable to import G-code");
  }

  return response.json() as Promise<ImportGcodeResult>;
}

export async function createJob(
  apiBaseUrl: string,
  artifactId: string,
  planningValues: PlanningValues,
): Promise<Job> {
  const response = await fetch(`${apiBaseUrl}/import/${artifactId}/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(planningValues),
  });

  if (!response.ok) {
    const error = new Error("Unable to create job") as CreateJobError;
    error.detail = (await response.json() as { detail?: unknown }).detail;
    throw error;
  }

  return response.json() as Promise<Job>;
}

export async function fetchQueue(apiBaseUrl: string): Promise<Queue> {
  const response = await fetch(`${apiBaseUrl}/queue`);

  if (!response.ok) {
    throw new Error("Unable to fetch active queue");
  }

  return response.json() as Promise<Queue>;
}

export async function updateJobScheduling(
  apiBaseUrl: string,
  jobId: string,
  schedulingData: { priority?: number; dueDate?: string | null; notes?: string | null; tags?: string[]; printerAssignment?: { mode: "preferred" | "required"; printerId: string } | null; expectedVersion: number },
): Promise<Job> {
  try {
    const client = new SchedulingClient({ BASE: apiBaseUrl, ENCODE_PATH: encodeURIComponent });
    return await client.default.updateJobSchedulingApiV1JobsJobIdSchedulingPatch({
      jobId,
      requestBody: schedulingData,
    }) as unknown as Job;
  } catch (error: unknown) {
    if (!(error instanceof ApiError)) throw error;
    throw new Error(error.status === 409
      ? "Scheduling has changed. Refresh the job before saving again."
      : "Unable to update job scheduling");
  }
}
