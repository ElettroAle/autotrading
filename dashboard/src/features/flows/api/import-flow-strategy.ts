import { useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { documentBody, readData, useApiClient } from '@/lib/api-client';
import type { components } from '@/lib/api-schema';

import { FLOWS_QUERY_KEY, flowsSchema, type Flow } from './get-flows';

const KILOBYTE = 1024;
const MAXIMUM_KILOBYTES = 64;

/** A file the browser refuses before sending it: the API decides everything else (ADR 0141). */
export class StrategyFileNotJsonError extends Error {
  constructor() {
    super('il file non è un JSON valido');
    this.name = 'StrategyFileNotJsonError';
  }
}

/** The name of the new flow and the file: only its size and its JSON are checked here (ADR 0141). */
export const importInputSchema = z.object({
  name: z.string().trim().min(1, 'nome del flusso obbligatorio'),
  files: z
    .custom<FileList>((files) => files instanceof FileList)
    .refine((files) => files.length === 1, 'scegli un file')
    .refine(
      (files) => [...files].every((file) => file.size <= MAXIMUM_KILOBYTES * KILOBYTE),
      `il file supera i ${MAXIMUM_KILOBYTES} KB`,
    ),
});

type StrategyDocument = components['schemas']['StrategyDocument-Input'];

export type ImportInput = z.infer<typeof importInputSchema>;

// The schema admits one file only: its text is the document.
const documentOf = async (files: FileList): Promise<string> => {
  const text = (await Promise.all([...files].map((file) => file.text()))).join('');
  try {
    JSON.parse(text);
  } catch {
    throw new StrategyFileNotJsonError();
  }
  return text;
};

/** A draft with the strategy of the file, sent as it is, under the name the user chose (R2.5.2, ADR 0140). */
export const useImportFlowStrategy = ({ onSuccess }: { onSuccess: (draft: Flow) => void }) => {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ name, files }: ImportInput) =>
      readData(
        await api.POST('/flows/import', {
          params: { query: { name } },
          ...documentBody<StrategyDocument>(await documentOf(files)),
        }),
        flowsSchema.element,
      ),
    onSuccess: async (draft) => {
      await queryClient.invalidateQueries({ queryKey: FLOWS_QUERY_KEY });
      onSuccess(draft);
    },
  });
};
