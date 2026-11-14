import { useMutation } from '@tanstack/react-query';

import { readFile, useApiClient } from '@/lib/api-client';

import { saveFile } from '../utils/save-file';

/**
 * Downloads the strategy file of the flow with the name the API gives it. The call carries the token of the user,
 * which a plain link would not (R2.5.2, ADR 0141).
 */
export const useExportFlowStrategy = () => {
  const api = useApiClient();
  return useMutation({
    mutationFn: async (flowId: string) =>
      readFile(
        await api.GET('/flows/{flow_id}/strategy', {
          params: { path: { flow_id: flowId } },
          parseAs: 'blob',
        }),
      ),
    onSuccess: saveFile,
  });
};
