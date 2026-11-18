import type { RouteObject } from 'react-router';

import { paths } from '@/config/paths';

import { AccountRoute } from './routes/app/account';
import { AccountAlarmsRoute } from './routes/app/account-alarms';
import { AccountCapitalRoute } from './routes/app/account-capital';
import { AccountOverviewRoute } from './routes/app/account-overview';
import { AccountReconciliationRoute } from './routes/app/account-reconciliation';
import { AccountSettingsRoute } from './routes/app/account-settings';
import { AccountsRoute } from './routes/app/accounts';
import { AlertRoute, AlertsRoute } from './routes/app/alerts';
import { ClosedPositionsRoute } from './routes/app/closed-positions';
import { ComparisonRoute } from './routes/app/comparison';
import { CycleRoute } from './routes/app/cycle';
import { CyclesRoute } from './routes/app/cycles';
import { DecisionsRoute } from './routes/app/decisions';
import { EditFlowRoute } from './routes/app/edit-flow';
import { FlowRoute } from './routes/app/flow';
import { FlowCapitalRoute } from './routes/app/flow-capital';
import { FlowOverviewRoute } from './routes/app/flow-overview';
import { FlowSettingsRoute, OldFlowVersionsRoute } from './routes/app/flow-settings';
import { GeneralSettingsRoute } from './routes/app/general-settings';
import { HistoryRoute } from './routes/app/history';
import { HomeRoute } from './routes/app/home';
import { NewFlowRoute } from './routes/app/new-flow';
import { NotificationsRoute } from './routes/app/notifications';
import { PositionsRoute } from './routes/app/positions';
import { ProviderKeysRoute } from './routes/app/provider-keys';
import { RankingRoute } from './routes/app/ranking';
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
      // The tabs of the page of the account live under its head, as those of the flow (ADR
      // elenco-dei-conti-e-pagina-del-conto); the address of its alarms of before leads to its alerts.
      {
        path: paths.account.path,
        element: <AccountRoute />,
        children: [
          { index: true, element: <AccountOverviewRoute /> },
          { path: paths.accountReconciliation.path, element: <AccountReconciliationRoute /> },
          { path: paths.accountCapital.path, element: <AccountCapitalRoute /> },
          { path: paths.accountSettings.path, element: <AccountSettingsRoute /> },
        ],
      },
      { path: paths.accountAlarms.path, element: <AccountAlarmsRoute /> },
      { path: paths.newFlow.path, element: <NewFlowRoute /> },
      // The tabs of the page of the flow live under its head and its period (R6.4.3).
      {
        path: paths.flow.path,
        element: <FlowRoute />,
        children: [
          { index: true, element: <FlowOverviewRoute /> },
          { path: paths.flowClosedPositions.path, element: <ClosedPositionsRoute /> },
          { path: paths.flowCycles.path, element: <CyclesRoute /> },
          { path: paths.flowDecisions.path, element: <DecisionsRoute /> },
          { path: paths.flowCapital.path, element: <FlowCapitalRoute /> },
        ],
      },
      { path: paths.editFlow.path, element: <EditFlowRoute /> },
      { path: paths.notifications.path, element: <NotificationsRoute /> },
      { path: paths.alerts.path, element: <AlertsRoute /> },
      { path: paths.alert.path, element: <AlertRoute /> },
      { path: paths.history.path, element: <HistoryRoute /> },
      { path: paths.generalSettings.path, element: <GeneralSettingsRoute /> },
      { path: paths.providerKeys.path, element: <ProviderKeysRoute /> },
      { path: paths.ranking.path, element: <RankingRoute /> },
      { path: paths.cycle.path, element: <CycleRoute /> },
      { path: paths.flowSettings.path, element: <FlowSettingsRoute /> },
      { path: paths.oldFlowVersions.path, element: <OldFlowVersionsRoute /> },
      { path: paths.flowPositions.path, element: <PositionsRoute /> },
      { path: paths.comparison.path, element: <ComparisonRoute /> },
    ],
  },
  { path: '*', element: <NotFoundRoute /> },
];
