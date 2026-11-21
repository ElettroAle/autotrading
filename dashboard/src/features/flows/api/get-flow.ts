import { useQuery } from '@tanstack/react-query';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

import { FLOWS_QUERY_KEY, flowSchema } from './get-flows';

/**
 * One flow of the tenant read alone, an archived one too, which the list leaves out, so its page opens from its address
 * (Bug 690, ADR pagina-del-flusso-archiviato-in-sola-lettura). Under the key of the flows, with its id: the commands
 * that read the flows again read it too.
 */
export const useFlow = (flowId: string) => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery(...FLOWS_QUERY_KEY, flowId),
    queryFn: async () =>
      readData(
        await api.GET('/flows/{flow_id}', { params: { path: { flow_id: flowId } } }),
        flowSchema,
      ),
  });
};
