import type { Page, Route } from '@playwright/test';
import { getResponse, type RequestHandler } from 'msw';

import { handlers } from '@/testing/mocks/handlers';
import { identityProviderHandlers } from '@/testing/mocks/identity-provider';

const IDENTITY_PROVIDER_ORIGIN = 'https://login.fake-idp.test';
const DASHBOARD_PATH = '/dashboard';

const requestOf = async (route: Route): Promise<Request> => {
  const request = route.request();
  const headers = Object.entries(await request.allHeaders()).filter(
    ([name]) => !name.startsWith(':'),
  );
  const hasBody = request.method() !== 'GET' && request.method() !== 'HEAD';
  return new Request(request.url(), {
    method: request.method(),
    headers,
    body: hasBody ? request.postData() : undefined,
  });
};

// The same MSW handlers of the unit tests answer the browser: one fake API and one fake identity provider (ADR 0116).
const answerWith = (fakes: RequestHandler[]) => async (route: Route) => {
  const response = await getResponse(fakes, await requestOf(route));
  if (response === undefined) {
    await route.fulfill({ status: 404 });
    return;
  }
  await route.fulfill({
    status: response.status,
    headers: Object.fromEntries(response.headers),
    body: Buffer.from(await response.arrayBuffer()),
  });
};

/** The dashboard is the real build served by its own server; the identity provider and the API are fakes. */
export const routeToFakes = async (page: Page, dashboardOrigin: string): Promise<void> => {
  await page.route(`${IDENTITY_PROVIDER_ORIGIN}/**`, answerWith(identityProviderHandlers));
  await page.route(
    (url) => url.origin === dashboardOrigin && !url.pathname.startsWith(DASHBOARD_PATH),
    answerWith(handlers),
  );
};
