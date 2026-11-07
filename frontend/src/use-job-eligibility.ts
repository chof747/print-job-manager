import { useMutation } from "@tanstack/react-query";

import { checkEligibility } from "./job-import-api-client";

export function useJobEligibility() {
  return useMutation({
    mutationFn: ({ apiBaseUrl, jobId, printerId }: {
      apiBaseUrl: string;
      jobId: string;
      printerId: string;
    }) => checkEligibility(apiBaseUrl, jobId, printerId),
  });
}
