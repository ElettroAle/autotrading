import { http } from 'msw';

import { server } from './mocks/server';

/**
 * The `from` of every request the dashboard makes to an endpoint of the fake API, in order; the fake answers as before.
 * A list keeps one interval while its period stays (ADR intervallo-delle-liste-fissato-alla-scelta-del-periodo). The
 * path names a resource of the test alone: a request of an earlier test still in flight goes to its own resource.
 */
export const requestedFrom = (path: string): string[] => {
  const asked: string[] = [];
  server.use(
    http.get(path, ({ request }) => {
      asked.push(new URL(request.url).searchParams.get('from') ?? '');
      // Without an answer the request goes on to the handler of the fake platform.
      return undefined;
    }),
  );
  return asked;
};
