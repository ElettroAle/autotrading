import { withComparedFlows } from '@/utils/compared-flows';

export const paths = {
  home: {
    path: '/',
    getHref: () => '/',
  },
  login: {
    path: '/login',
    getHref: (returnTo?: string) =>
      returnTo === undefined ? '/login' : `/login?returnTo=${encodeURIComponent(returnTo)}`,
  },
  accounts: {
    path: '/accounts',
    getHref: () => '/accounts',
  },
  // The history of the capital of an account, reached from the page of the accounts (R3.4.2).
  accountCapital: {
    path: '/accounts/:accountId/capital',
    getHref: (accountId: string) => `/accounts/${encodeURIComponent(accountId)}/capital`,
  },
  // The alarms of an account of before the alerts: the address leads to the alerts of the account (R6.2.3).
  accountAlarms: {
    path: '/accounts/:accountId/alarms',
    getHref: (accountId: string) => `/accounts/${encodeURIComponent(accountId)}/alarms`,
  },
  // Filters ride in the query string, so a filtered list has a link of its own (R6.4.4).
  alerts: {
    path: '/alerts',
    getHref: (filters: Readonly<Record<string, string>> = {}) => {
      const query = new URLSearchParams(filters).toString();
      return query === '' ? '/alerts' : `/alerts?${query}`;
    },
  },
  alert: {
    path: '/alerts/:alertId',
    getHref: (alertId: string) => `/alerts/${encodeURIComponent(alertId)}`,
  },
  newFlow: {
    path: '/flows/new',
    getHref: () => '/flows/new',
  },
  flow: {
    path: '/flows/:flowId',
    getHref: (flowId: string) => `/flows/${encodeURIComponent(flowId)}`,
  },
  editFlow: {
    path: '/flows/:flowId/edit',
    getHref: (flowId: string) => `/flows/${encodeURIComponent(flowId)}/edit`,
  },
  notifications: {
    path: '/notifications',
    getHref: () => '/notifications',
  },
  // Tab and filters ride in the query string, so a search of the history has a link of its own (ADR 0139).
  history: {
    path: '/history',
    getHref: () => '/history',
  },
  // The settings of the platform, not of the user, with the emergency closing of every flow (ADR
  // voce-generale-con-la-zona-pericolosa).
  generalSettings: {
    path: '/settings/general',
    getHref: () => '/settings/general',
  },
  providerKeys: {
    path: '/provider-keys',
    getHref: () => '/provider-keys',
  },
  // The cycles of a flow filtered on an outcome, as the failed cycles of its results lead to them (R6.4.2).
  flowCycles: {
    path: '/flows/:flowId/cycles',
    getHref: (flowId: string, page = 1, outcome = '') => {
      const search = new URLSearchParams();
      if (outcome !== '') {
        search.set('outcome', outcome);
      }
      if (page !== 1) {
        search.set('page', String(page));
      }
      const query = search.toString();
      return `/flows/${encodeURIComponent(flowId)}/cycles${query === '' ? '' : `?${query}`}`;
    },
  },
  flowDecisions: {
    path: '/flows/:flowId/decisions',
    getHref: (flowId: string, page = 1) =>
      `/flows/${encodeURIComponent(flowId)}/decisions${page === 1 ? '' : `?page=${page}`}`,
  },
  flowCapital: {
    path: '/flows/:flowId/capital',
    getHref: (flowId: string) => `/flows/${encodeURIComponent(flowId)}/capital`,
  },
  flowPositions: {
    path: '/flows/:flowId/positions',
    getHref: (flowId: string) => `/flows/${encodeURIComponent(flowId)}/positions`,
  },
  flowClosedPositions: {
    path: '/flows/:flowId/closed-positions',
    getHref: (flowId: string, page = 1) =>
      `/flows/${encodeURIComponent(flowId)}/closed-positions${page === 1 ? '' : `?page=${page}`}`,
  },
  // A cycle has a page of its own, so it can be shared as a link (ADR 0129).
  cycle: {
    path: '/flows/:flowId/cycles/:plannedAt',
    getHref: (flowId: string, plannedAt: string) =>
      `/flows/${encodeURIComponent(flowId)}/cycles/${encodeURIComponent(plannedAt)}`,
  },
  // Configuration, versions and the zone of danger of a flow, behind the gear of its page (ADR
  // impostazioni-del-flusso-dall-ingranaggio).
  flowSettings: {
    path: '/flows/:flowId/settings',
    getHref: (flowId: string) => `/flows/${encodeURIComponent(flowId)}/settings`,
  },
  // The old address of the configuration of a flow, which leads to its settings.
  oldFlowVersions: {
    path: '/flows/:flowId/versions',
    getHref: (flowId: string) => `/flows/${encodeURIComponent(flowId)}/versions`,
  },
  ranking: {
    path: '/ranking',
    getHref: () => '/ranking',
  },
  // The compared flows and the period travel in the query string, so the ranking links the comparison (ADR 0136).
  comparison: {
    path: '/comparison',
    getHref: (flowIds: readonly string[], periodSearch = '') =>
      `/comparison?${withComparedFlows(new URLSearchParams(periodSearch), flowIds).toString()}`,
  },
} as const;
