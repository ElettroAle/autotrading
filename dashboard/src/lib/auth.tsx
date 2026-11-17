import {
  AuthError,
  BrowserCacheLocation,
  CacheLookupPolicy,
  InteractionStatus,
  PublicClientApplication,
  type AuthenticationResult,
  type Configuration,
  type IPublicClientApplication,
} from '@azure/msal-browser';
import { MsalProvider, useMsal } from '@azure/msal-react';
import { createContext, use, useCallback, useEffect, type ReactNode } from 'react';
import { useLocation, useNavigate } from 'react-router';

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

/**
 * The page an automatic sign-in returns to, kept while the browser is at the identity provider. A load that finds it
 * and brings back no sign-in is the return of an automatic sign-in that failed, and starts no other one.
 */
export const AUTOMATIC_SIGN_IN_KEY = 'autotrading.dashboard.automatic-sign-in';

type AutomaticSignIn = 'allowed' | 'refused' | 'started';

// One automatic sign-in per load of the dashboard, so an identity provider that fails never makes the browser bounce
// (ADR accesso-persistente-con-cache-msal-in-localstorage).
const automaticSignIns = new WeakMap<IPublicClientApplication, AutomaticSignIn>();

export const authConfiguration = (settings: AuthSettings, redirectUri: string): Configuration => ({
  auth: {
    clientId: settings.clientId,
    authority: settings.issuer,
    // The issuer is the configuration of the installation: trusting it skips the discovery of the Microsoft clouds,
    // so another OIDC identity provider changes only the configuration (ADR 0118).
    knownAuthorities: [new URL(settings.issuer).host],
    redirectUri,
    postLogoutRedirectUri: redirectUri,
  },
  // The tokens outlive the tab and the browser, so the dashboard reopens without the credentials
  // (ADR accesso-persistente-con-cache-msal-in-localstorage).
  cache: { cacheLocation: BrowserCacheLocation.LocalStorage },
});

export const createAuthClient = (
  settings: AuthSettings,
  redirectUri: string,
): IPublicClientApplication =>
  new PublicClientApplication(authConfiguration(settings, redirectUri));

// Only a page of the dashboard itself: an address from outside could send the user elsewhere after the sign-in.
export const returnPathOf = (value: string | null | undefined): string =>
  value?.startsWith('/') === true && !value.startsWith('//') ? value : paths.home.getHref();

const takePendingReturn = (): string | null => {
  const pendingReturn = sessionStorage.getItem(AUTOMATIC_SIGN_IN_KEY);
  sessionStorage.removeItem(AUTOMATIC_SIGN_IN_KEY);
  return pendingReturn;
};

// The identity provider comes back with an error when the sign-in did not happen: nobody signed in.
const redirectResultOf = async (
  client: IPublicClientApplication,
): Promise<AuthenticationResult | null> => {
  try {
    return await client.handleRedirectPromise({ navigateToLoginRequestUrl: false });
  } catch (error) {
    if (error instanceof AuthError) {
      return null;
    }
    throw error;
  }
};

const activateCachedAccount = (client: IPublicClientApplication): void => {
  const [account] = client.getAllAccounts();
  if (client.getActiveAccount() === null && account !== undefined) {
    client.setActiveAccount(account);
  }
};

/**
 * Completes a sign-in coming back from the identity provider; returns the page the user was opening, also when an
 * automatic sign-in brought nobody back.
 */
export const completeSignIn = async (client: IPublicClientApplication): Promise<string | null> => {
  await client.initialize();
  const pendingReturn = takePendingReturn();
  const result = await redirectResultOf(client);
  if (result !== null) {
    client.setActiveAccount(result.account);
    automaticSignIns.set(client, 'allowed');
    return returnPathOf(result.state);
  }
  activateCachedAccount(client);
  automaticSignIns.set(client, pendingReturn === null ? 'allowed' : 'refused');
  return pendingReturn === null ? null : returnPathOf(pendingReturn);
};

/**
 * A token from the cache or renewed with the refresh token. No hidden frame (ADR 0118): when neither gives one, the
 * session is told expired and the dashboard renews it with a redirect.
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

/**
 * Starts, once per load, a redirect to the identity provider that comes back to the page: while its session lives it
 * asks no credentials (ADR accesso-persistente-con-cache-msal-in-localstorage). Tells whether a redirect is under way;
 * `onFailure` runs when it cannot start.
 */
export const startAutomaticSignIn = (
  client: IPublicClientApplication,
  scope: string,
  returnTo: string,
  onFailure: () => void,
): boolean => {
  const state = automaticSignIns.get(client) ?? 'allowed';
  if (state !== 'allowed') {
    return state === 'started';
  }
  automaticSignIns.set(client, 'started');
  sessionStorage.setItem(AUTOMATIC_SIGN_IN_KEY, returnTo);
  client
    .acquireTokenRedirect({
      scopes: [scope],
      state: returnTo,
      account: client.getActiveAccount() ?? undefined,
    })
    .catch(() => {
      sessionStorage.removeItem(AUTOMATIC_SIGN_IN_KEY);
      automaticSignIns.set(client, 'refused');
      onFailure();
    });
  return true;
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

/**
 * Renews an expired session with an automatic redirect to the identity provider; after one that failed in this load,
 * the sign-in page asks the user instead.
 */
export const useSessionRenewal = () => {
  const { instance } = useMsal();
  const scope = use(ScopeContext);
  const navigate = useNavigate();
  return useCallback(
    (returnTo: string) => {
      const openSignInPage = () => {
        void navigate(paths.login.getHref(returnTo), { replace: true });
      };
      if (!startAutomaticSignIn(instance, scope, returnTo, openSignInPage)) {
        openSignInPage();
      }
    },
    [instance, scope, navigate],
  );
};

/**
 * Signs out: the identity provider ends its session and MSAL empties its cache, so the browser keeps no token. Back
 * at the dashboard the sign-in page waits for the user, instead of an automatic sign-in.
 */
export const useSignOut = () => {
  const { instance } = useMsal();
  return useCallback(async () => {
    sessionStorage.setItem(AUTOMATIC_SIGN_IN_KEY, paths.home.getHref());
    await instance.logoutRedirect();
  }, [instance]);
};

const SignInRequired = ({ returnTo }: { returnTo: string }) => {
  const renewSession = useSessionRenewal();
  useEffect(() => {
    renewSession(returnTo);
  }, [renewSession, returnTo]);
  return null;
};

export const ProtectedRoute = ({ children }: { children: ReactNode }) => {
  const { accounts, inProgress } = useMsal();
  const location = useLocation();
  if (inProgress === InteractionStatus.Startup) {
    return null;
  }
  if (accounts.length === 0) {
    return <SignInRequired returnTo={`${location.pathname}${location.search}`} />;
  }
  return children;
};
