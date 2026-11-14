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
  providerKeys: {
    path: '/provider-keys',
    getHref: () => '/provider-keys',
  },
  flowCycles: {
    path: '/flows/:flowId/cycles',
    getHref: (flowId: string, page = 1) =>
      `/flows/${encodeURIComponent(flowId)}/cycles${page === 1 ? '' : `?page=${page}`}`,
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
  flowVersions: {
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
