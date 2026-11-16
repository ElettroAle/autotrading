import { useParams } from 'react-router';

import { CurrentOpenPositions } from '@/features/flow-positions/components/current-open-positions';
import { FlowStatistics } from '@/features/flow-statistics/components/flow-statistics';
import { ForecastAccuracy } from '@/features/flow-statistics/components/forecast-accuracy';
import { EquityCurve } from '@/features/flows/components/equity-curve';
import { FlowOpening } from '@/features/flows/components/flow-opening';

/**
 * The tab Panoramica: results, equity curve, statistics and error of the forecasts of the period, then the positions
 * held now (R6.4.3, R3.6.1).
 */
export const FlowOverviewRoute = () => {
  const { flowId = '' } = useParams();
  return (
    <>
      <FlowOpening flowId={flowId} />
      <EquityCurve flowId={flowId} />
      <FlowStatistics flowId={flowId} />
      <ForecastAccuracy flowId={flowId} />
      <CurrentOpenPositions flowId={flowId} />
    </>
  );
};
