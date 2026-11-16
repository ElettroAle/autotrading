import { http, HttpResponse } from 'msw';

import { accessTokenOf, fakePlatform } from './platform';

/**
 * A fake OIDC identity provider: discovery, authorization, credentials, token and sign-out endpoints. It keeps a session
 * after a sign-in, as Entra does: while the session lives a sign-in asks no credentials (R6.5.1). The access token is
 * the one the fake API recognises; the ID token carries the claims MSAL reads, unsigned, as the browser never verifies
 * it.
 */
export const FAKE_IDENTITY_PROVIDER = {
  issuer: 'https://login.fake-idp.test/tenant-1/v2.0',
  clientId: 'dashboard-client',
  scope: 'api://autotrading/access',
} as const;

const TENANT = 'tenant-1';
const HOUR = 3600;
const ENDPOINTS = 'https://login.fake-idp.test/tenant-1/oauth2/v2.0';
const CORS = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': '*' };

const base64Url = (text: string): string =>
  btoa(text).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');

const fromBase64Url = (text: string): string =>
  atob(text.replaceAll('-', '+').replaceAll('_', '/'));

const encoded = (value: object): string => base64Url(JSON.stringify(value));

const nowInSeconds = (): number => Math.floor(Date.now() / 1000);

const objectIdOf = (account: string): string => `oid-${account}`;

const idTokenOf = (account: string, nonce: string, now: number): string =>
  [
    encoded({ alg: 'none', typ: 'JWT' }),
    encoded({
      iss: FAKE_IDENTITY_PROVIDER.issuer,
      aud: FAKE_IDENTITY_PROVIDER.clientId,
      sub: objectIdOf(account),
      oid: objectIdOf(account),
      tid: TENANT,
      name: account,
      preferred_username: `${account}@example.test`,
      // The user chose «Rimani connesso»: MSAL keeps the tokens readable after the browser closes (R6.5.1).
      signin_state: ['kmsi'],
      nonce,
      iat: now,
      nbf: now,
      exp: now + HOUR,
    }),
    'signature',
  ].join('.');

export const tokenResponseOf = (account: string, nonce = '', now = nowInSeconds()) => ({
  token_type: 'Bearer' as const,
  scope: FAKE_IDENTITY_PROVIDER.scope,
  expires_in: HOUR,
  ext_expires_in: HOUR,
  access_token: accessTokenOf(account),
  refresh_token: `fake-refresh-token-${account}`,
  id_token: idTokenOf(account, nonce, now),
  client_info: encoded({ uid: objectIdOf(account), utid: TENANT }),
});

type AuthorizationCode = { readonly account: string; readonly nonce: string };

const authorizationCodeOf = (code: string): AuthorizationCode =>
  JSON.parse(fromBase64Url(code)) as AuthorizationCode;

const accountOfRefreshToken = (token: string): string => token.replace('fake-refresh-token-', '');

const escapedHtml = (text: string): string =>
  text
    .replaceAll('&', '&amp;')
    .replaceAll('"', '&quot;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');

const page = (body: string): Response =>
  new HttpResponse(
    `<!doctype html><html lang="it"><head><title>Accesso</title></head><body>${body}</body></html>`,
    {
      headers: { 'Content-Type': 'text/html' },
    },
  );

const navigateTo = (location: string): Response =>
  page(`<script>location.replace(${JSON.stringify(location)})</script>`);

// The identity provider sends the browser back to the dashboard with the code, or with the error, of the request.
const backToDashboard = (parameters: URLSearchParams, account: string | undefined): Response => {
  const response = new URLSearchParams({ state: parameters.get('state') ?? '' });
  if (account === undefined) {
    response.set('error', 'login_required');
  } else {
    response.set('code', encoded({ account, nonce: parameters.get('nonce') ?? '' }));
    response.set('client_info', encoded({ uid: objectIdOf(account), utid: TENANT }));
  }
  const separator = parameters.get('response_mode') === 'query' ? '?' : '#';
  return navigateTo(`${parameters.get('redirect_uri') ?? ''}${separator}${response.toString()}`);
};

// The page where the user types the credentials: the request travels with the form, as Entra keeps it.
const credentialsPage = (parameters: URLSearchParams): Response => {
  fakePlatform.countCredentialPage();
  return page(
    `<h1>Inserisci le credenziali</h1><form method="post" action="${ENDPOINTS}/credentials">` +
      `<input type="hidden" name="request" value="${escapedHtml(parameters.toString())}">` +
      '<button type="submit">Invia le credenziali</button></form>',
  );
};

const INTERACTIVE_PROMPTS = new Set(['login', 'select_account', 'consent']);

const authorize = (url: URL): Response => {
  const parameters = url.searchParams;
  const prompt = parameters.get('prompt') ?? '';
  if (prompt === 'none') {
    return backToDashboard(parameters, fakePlatform.identityProviderSession());
  }
  const session = fakePlatform.identityProviderSession();
  if (session !== undefined && !INTERACTIVE_PROMPTS.has(prompt)) {
    return backToDashboard(parameters, session);
  }
  return credentialsPage(parameters);
};

// The credentials sent start the session of the account; without an account the page asks again.
const credentials = async (request: Request): Promise<Response> => {
  const parameters = new URLSearchParams(
    new URLSearchParams(await request.text()).get('request') ?? '',
  );
  const account = fakePlatform.takeSigningInAccount();
  if (account === undefined) {
    return credentialsPage(parameters);
  }
  fakePlatform.startIdentityProviderSession(account);
  return backToDashboard(parameters, account);
};

const signOut = (url: URL): Response => {
  fakePlatform.endIdentityProviderSession();
  return navigateTo(url.searchParams.get('post_logout_redirect_uri') ?? '');
};

const token = async (request: Request): Promise<Response> => {
  const form = new URLSearchParams(await request.text());
  if (form.get('grant_type') === 'refresh_token') {
    if (fakePlatform.refreshTokensExpired()) {
      return HttpResponse.json(
        {
          error: 'invalid_grant',
          error_description: 'the refresh token has expired',
          suberror: 'bad_token',
        },
        { status: 400, headers: CORS },
      );
    }
    return HttpResponse.json(
      tokenResponseOf(accountOfRefreshToken(form.get('refresh_token') ?? '')),
      {
        headers: CORS,
      },
    );
  }
  const code = authorizationCodeOf(form.get('code') ?? '');
  return HttpResponse.json(tokenResponseOf(code.account, code.nonce), { headers: CORS });
};

export const identityProviderHandlers = [
  http.get(`${FAKE_IDENTITY_PROVIDER.issuer}/.well-known/openid-configuration`, () =>
    HttpResponse.json(
      {
        issuer: FAKE_IDENTITY_PROVIDER.issuer,
        authorization_endpoint: `${ENDPOINTS}/authorize`,
        token_endpoint: `${ENDPOINTS}/token`,
        end_session_endpoint: `${ENDPOINTS}/logout`,
        jwks_uri: 'https://login.fake-idp.test/tenant-1/discovery/v2.0/keys',
        response_modes_supported: ['query', 'fragment', 'form_post'],
      },
      { headers: CORS },
    ),
  ),
  http.get(`${ENDPOINTS}/authorize`, ({ request }) => authorize(new URL(request.url))),
  http.post(`${ENDPOINTS}/credentials`, ({ request }) => credentials(request)),
  http.get(`${ENDPOINTS}/logout`, ({ request }) => signOut(new URL(request.url))),
  http.options(`${ENDPOINTS}/token`, () => new HttpResponse(null, { status: 204, headers: CORS })),
  http.post(`${ENDPOINTS}/token`, ({ request }) => token(request)),
];
