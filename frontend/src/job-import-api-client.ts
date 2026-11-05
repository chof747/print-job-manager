import { ApiError } from "./generated/scheduling/core/ApiError";
import { SchedulingClient } from "./generated/scheduling/SchedulingClient";
import type { SchedulingJobResponse } from "./generated/scheduling/models/SchedulingJobResponse";
import type { UpdateSchedulingRequest } from "./generated/scheduling/models/UpdateSchedulingRequest";

export type ImportedArtifact = {
  id: string;
  filename: string;
};

export type ImportGcodeResult = {
  artifact: ImportedArtifact;
  import?: { id: string };
  extractedMetadata?: Record<string, string | number>;
  provenance?: Record<string, { parser: string; sourceKey: string }>;
  diagnostics?: Array<{ code: string; sourceKey: string }>;
  missingPlanningValues: string[];
};

export type Job = SchedulingJobResponse;

export type Queue = {
  jobs: Job[];
};

export type Cockpit = {
  activeJobs: Job[];
  failures: Job[];
  recentHistory: Job[];
};

export async function fetchCockpit(apiBaseUrl: string, filters = ""): Promise<Cockpit> {
  const params = new URLSearchParams(filters);
  const text = (key: string) => params.get(key) ?? undefined;
  const number = (key: string) => params.has(key) ? Number(params.get(key)) : undefined;
  const client = new SchedulingClient({ BASE: apiBaseUrl, ENCODE_PATH: encodeURIComponent });
  try {
    return await client.default.cockpitApiV1CockpitGet({
      diagnosticCode: text("diagnosticCode"), material: text("material"),
      minDurationSeconds: number("minDurationSeconds"), minPriority: number("minPriority"),
      dueBefore: text("dueBefore"), tag: text("tag"), assignmentMode: text("assignmentMode"),
      maxFilamentWeightGrams: number("maxFilamentWeightGrams"), nozzleDiameter: number("nozzleDiameter"),
      maxDimensionX: number("maxDimensionX"), maxDimensionY: number("maxDimensionY"),
      maxDimensionZ: number("maxDimensionZ"), slicer: text("slicer"),
      provenanceParser: text("provenanceParser"),
    });
  } catch {
    throw new Error("Unable to fetch cockpit");
  }
}

export async function fetchJob(apiBaseUrl: string, jobId: string): Promise<Job> {
  const client = new SchedulingClient({ BASE: apiBaseUrl, ENCODE_PATH: encodeURIComponent });
  try {
    return await client.default.jobDetailApiV1JobsJobIdGet({ jobId });
  } catch {
    throw new Error("Unable to fetch job details");
  }
}

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

export async function fetchImportReview(apiBaseUrl: string, importId: string): Promise<ImportGcodeResult> {
  const response = await fetch(`${apiBaseUrl}/import/${encodeURIComponent(importId)}`);
  if (!response.ok) {
    throw new Error("Unable to load import review");
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
  schedulingData: UpdateSchedulingRequest,
): Promise<Job> {
  try {
    const client = new SchedulingClient({ BASE: apiBaseUrl, ENCODE_PATH: encodeURIComponent });
    return await client.default.updateJobSchedulingApiV1JobsJobIdSchedulingPatch({
      jobId,
      requestBody: schedulingData,
    });
  } catch (error: unknown) {
    if (!(error instanceof ApiError)) throw error;
    throw new Error(error.status === 409
      ? "Scheduling has changed. Refresh the job before saving again."
      : "Unable to update job scheduling");
  }
}
