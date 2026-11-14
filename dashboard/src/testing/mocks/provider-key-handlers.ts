import { http, HttpResponse } from 'msw';

import { fakePlatform, type FakeProviderKey, type FakeUser } from './platform';
import { problem, textFieldsOf, withUser } from './responses';

/** The providers of the catalog of the fake platform: a key is accepted only for one of them (R1.4.1). */
export const FAKE_PROVIDERS = ['anthropic', 'openai', 'openrouter'] as const;

const providerOf = (name: string): string => name.trim().toLowerCase();

const responseOf = (key: FakeProviderKey) => ({
  provider: key.provider,
  registered_at: key.registeredAt,
});

// The key is never asked to the provider: only presence and catalog (R1.4.1, ADR 0108).
const refusalOfKey = (provider: string, key: string): Response | undefined => {
  if (key.trim() === '') {
    return problem(422, 'Unprocessable Content', 'chiave obbligatoria');
  }
  if (!FAKE_PROVIDERS.some((known) => known === provider)) {
    return problem(422, 'Unprocessable Content', `fornitore non supportato: ${provider}`, {
      supported: [...FAKE_PROVIDERS],
    });
  }
  return undefined;
};

const notRegistered = (provider: string) =>
  problem(404, 'Not Found', `nessuna chiave registrata per il fornitore: ${provider}`);

const keyOf = (user: FakeUser, provider: string) =>
  fakePlatform.providerKeyOf(user.account, provider);

export const providerKeyHandlers = [
  http.get('*/provider-keys', ({ request }) =>
    withUser(request, (user) =>
      HttpResponse.json(
        [...user.providerKeys]
          .sort((one, other) => one.provider.localeCompare(other.provider))
          .map(responseOf),
      ),
    ),
  ),
  http.post('*/provider-keys', ({ request }) =>
    withUser(request, async (user) => {
      const fields = await textFieldsOf(request);
      const provider = providerOf(fields.provider ?? '');
      const refusal = refusalOfKey(provider, fields.key ?? '');
      if (refusal !== undefined) {
        return refusal;
      }
      if (keyOf(user, provider) !== undefined) {
        return problem(409, 'Conflict', `chiave già registrata per il fornitore: ${provider}`);
      }
      const saved = fakePlatform.saveProviderKey(user.account, provider, new Date().toISOString());
      return HttpResponse.json(responseOf(saved), { status: 201 });
    }),
  ),
  http.put('*/provider-keys/:provider', ({ request, params }) =>
    withUser(request, async (user) => {
      const fields = await textFieldsOf(request);
      const provider = providerOf(String(params.provider));
      const refusal = refusalOfKey(provider, fields.key ?? '');
      if (refusal !== undefined) {
        return refusal;
      }
      if (keyOf(user, provider) === undefined) {
        return notRegistered(provider);
      }
      const saved = fakePlatform.saveProviderKey(user.account, provider, new Date().toISOString());
      return HttpResponse.json(responseOf(saved));
    }),
  ),
  http.delete('*/provider-keys/:provider', ({ request, params }) =>
    withUser(request, (user) => {
      const provider = providerOf(String(params.provider));
      const key = keyOf(user, provider);
      if (key === undefined) {
        return notRegistered(provider);
      }
      user.providerKeys.splice(user.providerKeys.indexOf(key), 1);
      return new HttpResponse(null, { status: 204 });
    }),
  ),
];
