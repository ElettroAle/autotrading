import { PublicClientApplication } from '@azure/msal-browser';

import { FAKE_IDENTITY_PROVIDER } from './mocks/identity-provider';
import { authClientFor } from './test-utils';

const PENDING = 'pending';

const outcomeOf = (redirect: Promise<void>): Promise<string> =>
  Promise.race([
    redirect.then(
      () => 'resolved',
      () => 'rejected',
    ),
    new Promise<string>((resolve) => setTimeout(() => resolve(PENDING), 200)),
  ]);

describe('authClientFor', () => {
  // ADR redirect-dell-accesso-che-non-torna-nei-test: a redirect leaves the page, so its promise never settles; one
  // that settled after the end of a test would run on a closed jsdom.
  it.each([
    ['a visitor', undefined],
    ['a signed-in user', 'anna'],
  ])(
    'gives %s a redirect to the identity provider that never comes back (ADR redirect-dell-accesso-che-non-torna-nei-test)',
    async (_who, account) => {
      const client = await authClientFor(account);

      const redirect = client.acquireTokenRedirect({ scopes: [FAKE_IDENTITY_PROVIDER.scope] });

      await expect(outcomeOf(redirect)).resolves.toBe(PENDING);
    },
  );

  it('leaves the redirect to a test that replaces it on every client of MSAL', async () => {
    const redirect = vi
      .spyOn(PublicClientApplication.prototype, 'acquireTokenRedirect')
      .mockResolvedValue();
    const client = await authClientFor();

    await client.acquireTokenRedirect({ scopes: [FAKE_IDENTITY_PROVIDER.scope] });

    expect(redirect).toHaveBeenCalledWith({ scopes: [FAKE_IDENTITY_PROVIDER.scope] });
    redirect.mockRestore();
  });
});
