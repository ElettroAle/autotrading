import { Navigate, useParams } from 'react-router';

import { paths } from '@/config/paths';

/**
 * The alarms of an account are its alerts now: the address of before leads to the alerts of the account, in every
 * state, so a link kept from before still works (R6.2.3, ADR pagina-avvisi-nella-dashboard).
 */
export const AccountAlarmsRoute = () => {
  const { accountId = '' } = useParams();
  return <Navigate replace to={paths.alerts.getHref({ resource_id: accountId, state: 'all' })} />;
};
