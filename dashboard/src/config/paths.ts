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
  flow: {
    path: '/flows/:flowId',
    getHref: (flowId: string) => `/flows/${encodeURIComponent(flowId)}`,
  },
  notifications: {
    path: '/notifications',
    getHref: () => '/notifications',
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
} as const;
