import {
  BrowserCacheLocation,
  CacheLookupPolicy,
  InteractionStatus,
  PublicClientApplication,
  type Configuration,
  type IPublicClientApplication,
} from '@azure/msal-browser';
import { MsalProvider, useMsal } from '@azure/msal-react';
import { createContext, use, useCallback, type ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router';

import { paths } from '@/config/paths';

/** Authorization code flow with PKCE for a public client: the browser keeps no secret (ADR 0118). */
export type AuthSettings = {
  readonly issuer: string;
  readonly clientId: string;
  readonly scope: string;
};

export class SessionExpiredError extends Error {
  constructor(options?: ErrorOptions) {
    super('sessione scaduta', options);
    this.name = 'SessionExpiredError';
  }
}

export const authConfiguration = (settings: AuthSettings, redirectUri: string): Configuration => ({
  auth: {
    clientId: settings.clientId,
    authority: settings.issuer,
    // The issuer is the configuration of the installation: trusting it skips the discovery of the Microsoft clouds,
    // so another OIDC identity provider changes only the configuration (ADR 0118).
    knownAuthorities: [new URL(settings.issuer).host],
    redirectUri,
  },
  // Closing the tab ends the session: no token survives in localStorage (ADR 0118).
  cache: { cacheLocation: BrowserCacheLocation.SessionStorage },
});

export const createAuthClient = (
  settings: AuthSettings,
  redirectUri: string,
): IPublicClientApplication =>
  new PublicClientApplication(authConfiguration(settings, redirectUri));

// Only a page of the dashboard itself: an address from outside could send the user elsewhere after the sign-in.
export const returnPathOf = (value: string | null | undefined): string =>
  value?.startsWith('/') === true && !value.startsWith('//') ? value : paths.home.getHref();

/** Completes a sign-in coming back from the identity provider; returns the page the user was opening. */
export const completeSignIn = async (client: IPublicClientApplication): Promise<string | null> => {
  await client.initialize();
  const result = await client.handleRedirectPromise({ navigateToLoginRequestUrl: false });
  if (result !== null) {
    client.setActiveAccount(result.account);
    return returnPathOf(result.state);
  }
  const [account] = client.getAllAccounts();
  if (client.getActiveAccount() === null && account !== undefined) {
    client.setActiveAccount(account);
  }
  return null;
};

/**
 * A token from the cache or renewed with the refresh token. No hidden frame: an expired session is told at once and
 * the user signs in again (ADR 0118).
 */
export const acquireAccessToken = async (
  client: IPublicClientApplication,
  scope: string,
): Promise<string> => {
  const account = client.getActiveAccount();
  if (account === null) {
    throw new SessionExpiredError();
  }
  try {
    const result = await client.acquireTokenSilent({
      account,
      scopes: [scope],
      cacheLookupPolicy: CacheLookupPolicy.AccessTokenAndRefreshToken,
    });
    return result.accessToken;
  } catch (error) {
    throw new SessionExpiredError({ cause: error });
  }
};

const ScopeContext = createContext('');

export const AuthProvider = ({
  client,
  scope,
  children,
}: {
  client: IPublicClientApplication;
  scope: string;
  children: ReactNode;
}) => (
  <MsalProvider instance={client}>
    <ScopeContext value={scope}>{children}</ScopeContext>
  </MsalProvider>
);

export const useSignIn = () => {
  const { instance } = useMsal();
  const scope = use(ScopeContext);
  return useCallback(
    (returnTo: string) => instance.loginRedirect({ scopes: [scope], state: returnTo }),
    [instance, scope],
  );
};

export const useAccessToken = () => {
  const { instance } = useMsal();
  const scope = use(ScopeContext);
  return useCallback(() => acquireAccessToken(instance, scope), [instance, scope]);
};

export const ProtectedRoute = ({ children }: { children: ReactNode }) => {
  const { accounts, inProgress } = useMsal();
  const location = useLocation();
  if (inProgress === InteractionStatus.Startup) {
    return null;
  }
  if (accounts.length === 0) {
    return <Navigate to={paths.login.getHref(`${location.pathname}${location.search}`)} replace />;
  }
  return children;
};
