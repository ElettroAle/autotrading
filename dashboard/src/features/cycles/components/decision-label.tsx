import { ActionLabel } from '@/components/ui/action-label';
import { DirectionLabel } from '@/components/ui/direction-label';

import type { Decision } from '../utils/cycle-documents';

/** A decision of the agent in a few words, «apri long BTC», action and direction each with its icon (R6.5.3). */
export const DecisionLabel = ({ decision }: { readonly decision: Decision }) => {
  const direction = decision.opening?.direction;
  return (
    <span>
      <ActionLabel value={decision.action} />{' '}
      {direction !== undefined && (
        <>
          <DirectionLabel value={direction} />{' '}
        </>
      )}
      {decision.asset}
    </span>
  );
};
