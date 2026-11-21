import { useFlow } from '../api/get-flow';

/**
 * The title of a page of the flow, once the page has read it: its name, or what the page shows of it with its name,
 * «Cicli di prova-btc» (R6.4.1, ADR viste-e-comandi-della-pagina-del-flusso). Before, the title says only the subject.
 */
export const useFlowTitle = (flowId: string, subject?: string): string => {
  const name = useFlow(flowId).data?.name;
  if (subject === undefined) {
    return name ?? 'Flusso';
  }
  return name === undefined ? `${subject} del flusso` : `${subject} di ${name}`;
};
