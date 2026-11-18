import { useMutation, useQueryClient } from '@tanstack/react-query';

import { readDone, useApiClient, type ApiClient } from '@/lib/api-client';

import type { AlertDetail, AlertCommand } from './get-alert';

// The confirmation and the resumption are the commands the API already has on the account and on the flow: only the
// resolution by hand belongs to the alert (ADR api-degli-avvisi-e-link-nelle-notifiche).
const sendCommand = (api: ApiClient, alert: AlertDetail, command: AlertCommand) => {
  if (command === 'confirm_reconciliation') {
    return api.POST('/accounts/{account_id}/reconciliation/confirmation', {
      params: { path: { account_id: alert.resource.id } },
    });
  }
  if (command === 'resume_flow') {
    return api.POST('/flows/{flow_id}/{action}', {
      params: { path: { flow_id: alert.resource.id, action: 'resume' } },
    });
  }
  return api.POST('/alerts/{alert_id}/resolution', { params: { path: { alert_id: alert.id } } });
};

/** A command that resolves the alert, then every page data read again: the alert, the menu and the resource. */
export const useRunAlertCommand = (alert: AlertDetail) => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (command: AlertCommand) => readDone(await sendCommand(api, alert, command)),
    onSettled: () => queryClient.invalidateQueries(),
  });
};
