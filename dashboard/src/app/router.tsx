import type { RouteObject } from 'react-router';

import { paths } from '@/config/paths';

import { AccountsRoute } from './routes/app/accounts';
import { ClosedPositionsRoute } from './routes/app/closed-positions';
import { CycleRoute } from './routes/app/cycle';
import { CyclesRoute } from './routes/app/cycles';
import { EditFlowRoute } from './routes/app/edit-flow';
import { FlowRoute } from './routes/app/flow';
import { FlowVersionsRoute } from './routes/app/flow-versions';
import { HistoryRoute } from './routes/app/history';
import { HomeRoute } from './routes/app/home';
import { NewFlowRoute } from './routes/app/new-flow';
import { NotificationsRoute } from './routes/app/notifications';
import { PositionsRoute } from './routes/app/positions';
import { ProviderKeysRoute } from './routes/app/provider-keys';
import { AppRoot } from './routes/app/root';
import { LoginRoute } from './routes/login';
import { NotFoundRoute } from './routes/not-found';

/** The dashboard lives under /dashboard on the name of the installation, beside the API (ADR 0117). */
export const BASE_NAME = '/dashboard';

export const routes: RouteObject[] = [
  { path: paths.login.path, element: <LoginRoute /> },
  {
    path: paths.home.path,
    element: <AppRoot />,
    children: [
      { index: true, element: <HomeRoute /> },
      { path: paths.accounts.path, element: <AccountsRoute /> },
      { path: paths.newFlow.path, element: <NewFlowRoute /> },
      { path: paths.flow.path, element: <FlowRoute /> },
      { path: paths.editFlow.path, element: <EditFlowRoute /> },
      { path: paths.notifications.path, element: <NotificationsRoute /> },
      { path: paths.history.path, element: <HistoryRoute /> },
      { path: paths.providerKeys.path, element: <ProviderKeysRoute /> },
      { path: paths.flowCycles.path, element: <CyclesRoute /> },
      { path: paths.cycle.path, element: <CycleRoute /> },
      { path: paths.flowVersions.path, element: <FlowVersionsRoute /> },
      { path: paths.flowPositions.path, element: <PositionsRoute /> },
      { path: paths.flowClosedPositions.path, element: <ClosedPositionsRoute /> },
    ],
  },
  { path: '*', element: <NotFoundRoute /> },
];
