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
} as const;
