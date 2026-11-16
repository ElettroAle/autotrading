import { Navigate, useLocation, useParams } from 'react-router';

import { paths } from '@/config/paths';

/** The open positions are in the overview of the flow (R6.4.3): their old address leads there, with its period. */
export const PositionsRoute = () => {
  const { flowId = '' } = useParams();
  const { search } = useLocation();
  return <Navigate to={`${paths.flow.getHref(flowId)}${search}`} replace />;
};
