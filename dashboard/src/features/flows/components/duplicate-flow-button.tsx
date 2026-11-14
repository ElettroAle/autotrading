import { useNavigate } from 'react-router';

import { paths } from '@/config/paths';

import { useDuplicateFlow } from '../api/duplicate-flow';

import { CommandRefusal } from './command-refusal';

/** Duplicates the flow and opens the draft, where the user assigns account, capital and assets (ADR 0125). */
export const DuplicateFlowButton = ({ flowId }: { flowId: string }) => {
  const navigate = useNavigate();
  const duplicate = useDuplicateFlow({
    onSuccess: (copy) => {
      void navigate(paths.flow.getHref(copy.id));
    },
  });
  return (
    <div>
      <button
        type="button"
        disabled={duplicate.isPending}
        onClick={() => duplicate.mutate(flowId)}
        className="rounded border border-slate-300 px-3 py-1 hover:bg-slate-100"
      >
        Duplica
      </button>
      <CommandRefusal refusal="Duplicazione rifiutata" error={duplicate.error} />
    </div>
  );
};
