import { useId } from 'react';

import { Card } from '@/components/ui/card';

import { OpenPositions } from './open-positions';

/**
 * The positions the flow holds now, in the overview of the flow: the period of the page does not narrow them, and the
 * panel says so (R6.4.3).
 */
export const CurrentOpenPositions = ({ flowId }: { flowId: string }) => {
  const titleId = useId();
  return (
    <Card as="section" aria-labelledby={titleId} className="mt-4">
      <h3 id={titleId} className="text-lg font-semibold">
        Posizioni aperte attuali
      </h3>
      <p className="mb-3 text-sm text-slate-600">
        Le posizioni aperte adesso, qualunque sia il periodo scelto.
      </p>
      <OpenPositions flowId={flowId} />
    </Card>
  );
};
