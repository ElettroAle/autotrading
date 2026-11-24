import { useParams } from 'react-router';

import { FlowMemory } from '@/features/flow-memory/components/flow-memory';
import { CurrentOpenPositions } from '@/features/flow-positions/components/current-open-positions';
import { FlowStatistics } from '@/features/flow-statistics/components/flow-statistics';
import { ForecastAccuracy } from '@/features/flow-statistics/components/forecast-accuracy';
import { EquityCurve } from '@/features/flows/components/equity-curve';
import { FlowOpening } from '@/features/flows/components/flow-opening';
import { LastDecision } from '@/features/last-decision/components/last-decision';

/**
 * The tab Panoramica: results, the last decision of the agent whatever the period, the memory it will receive when the
 * memory is on, equity curve, statistics and error of the forecasts of the period, then the positions held now (R6.4.3,
 * R3.6.1, R6.5.4, R5.3.4).
 */
export const FlowOverviewRoute = () => {
  const { flowId = '' } = useParams();
  return (
    <>
      <FlowOpening flowId={flowId} />
      <LastDecision flowId={flowId} />
      <FlowMemory flowId={flowId} />
      <EquityCurve flowId={flowId} />
      <FlowStatistics flowId={flowId} />
      <ForecastAccuracy flowId={flowId} />
      <CurrentOpenPositions flowId={flowId} />
    </>
  );
};
