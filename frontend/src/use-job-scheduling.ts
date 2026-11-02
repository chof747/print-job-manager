import { useMutation } from "@tanstack/react-query";

import type { UpdateSchedulingRequest } from "./generated/scheduling/models/UpdateSchedulingRequest";
import { updateJobScheduling } from "./job-import-api-client";

export function useJobScheduling() {
  return useMutation({
    mutationFn: ({ apiBaseUrl, jobId, changes }: {
      apiBaseUrl: string;
      jobId: string;
      changes: UpdateSchedulingRequest;
    }) => updateJobScheduling(apiBaseUrl, jobId, changes),
  });
}
