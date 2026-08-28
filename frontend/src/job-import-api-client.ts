export type ImportedArtifact = {
  id: string;
  filename: string;
};

export type ImportGcodeResult = {
  artifact: ImportedArtifact;
  missingPlanningValues: string[];
};

export type Job = {
  id: string;
  state: string;
  executionData: {
    artifactRef: string;
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

/**
 * Typed API operations shaped for replacement by an OpenAPI generator.
 * The implementation remains local until generation is introduced.
 */
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
