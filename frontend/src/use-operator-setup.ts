import { QueryClient, QueryClientContext, useMutation } from "@tanstack/react-query";
import { useContext, useState } from "react";

import { SchedulingClient } from "./generated/scheduling/SchedulingClient";
import type { MaterialInventoryRequest } from "./generated/scheduling/models/MaterialInventoryRequest";
import type { PrinterCapabilitiesRequest } from "./generated/scheduling/models/PrinterCapabilitiesRequest";

export function useOperatorSetup(apiBaseUrl: string) {
  const contextClient = useContext(QueryClientContext);
  const [fallbackClient] = useState(() => new QueryClient());
  const queryClient = contextClient ?? fallbackClient;
  const client = new SchedulingClient({ BASE: apiBaseUrl, ENCODE_PATH: encodeURIComponent });
  const printer = useMutation({
    mutationFn: ({ printerId, capabilities }: { printerId: string; capabilities: PrinterCapabilitiesRequest }) =>
      client.default.putPrinterApiV1PrintersPrinterIdPut({ printerId, requestBody: capabilities }),
    onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ["printers", apiBaseUrl] }); },
  }, queryClient);
  const material = useMutation({
    mutationFn: (requestBody: MaterialInventoryRequest) =>
      client.default.addInventoryMaterialApiV1InventoryMaterialsPost({ requestBody }),
  }, queryClient);
  return { printer, material };
}
