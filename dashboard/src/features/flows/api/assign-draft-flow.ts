import { useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';

import { FLOWS_QUERY_KEY, flowsSchema } from './get-flows';

const POSITIVE_AMOUNT = /^\d+(\.\d+)?$/;

/** What the user writes in the form: the API decides the rest, the form only asks for every field (ADR 0125). */
export const assignmentInputSchema = z.object({
  accountId: z.string().min(1, 'scegli un conto'),
  allocatedCapital: z
    .string()
    .trim()
    .refine(
      (amount) => POSITIVE_AMOUNT.test(amount) && Number(amount) > 0,
      'il capitale allocato deve essere positivo',
    ),
  assets: z.string().trim().min(1, 'almeno un asset è obbligatorio'),
});

export type AssignmentInput = z.infer<typeof assignmentInputSchema>;

const requestOf = ({ accountId, allocatedCapital, assets }: AssignmentInput) => ({
  account_id: accountId,
  // The amount travels as text, so no digit is rounded on the way (ADR 0018).
  allocated_capital: allocatedCapital.trim(),
  assets: assets
    .split(',')
    .map((asset) => asset.trim())
    .filter((asset) => asset !== ''),
});

/** Account, capital and assets the draft will start with (R2.4.1, ADR 0124). */
export const useAssignDraftFlow = (flowId: string) => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: AssignmentInput) =>
      readData(
        await api.PUT('/flows/{flow_id}/assignment', {
          params: { path: { flow_id: flowId } },
          body: requestOf(input),
        }),
        flowsSchema.element,
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: FLOWS_QUERY_KEY }),
  });
};
