import { useNavigate } from 'react-router';

import { CommandRefusal } from '@/components/ui/command-refusal';
import { SECONDARY_COMMAND } from '@/components/ui/commands';
import { paths } from '@/config/paths';

import { useDuplicateFlow } from '../api/duplicate-flow';

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
        className={SECONDARY_COMMAND}
      >
        Duplica
      </button>
      <CommandRefusal refusal="Duplicazione rifiutata" error={duplicate.error} />
    </div>
  );
};
