import { http, HttpResponse } from 'msw';

import { enteredExpiryOf } from './key-expiry';
import { problem, textFieldsOf, textFieldsWithin, withUser } from './responses';
import { fakeSourceCredentials } from './source-credentials';

const notFound = (adapter: string) =>
  problem(404, 'Not Found', `credenziali dell'adapter non trovate: ${adapter}`);

// The rules of the domain of the API on the values, with their reasons (R4.1.2).
const refusalOfValues = (
  fields: readonly { readonly name: string; readonly label: string }[],
  values: Record<string, string>,
): Response | undefined => {
  const unknown = Object.keys(values).find((name) => !fields.some((field) => field.name === name));
  if (unknown !== undefined) {
    return problem(422, 'Unprocessable Content', `campo non previsto: ${unknown}`, {
      field: unknown,
    });
  }
  const missing = fields.find((field) => (values[field.name] ?? '').trim() === '');
  if (missing !== undefined) {
    const label = `${missing.label.charAt(0).toLowerCase()}${missing.label.slice(1)}`;
    return problem(422, 'Unprocessable Content', `${label} obbligatorio`, { field: missing.name });
  }
  return undefined;
};

/** The section Fonti of the page of the keys on the fake API (R4.1.2, ADR credenziali-degli-adapter-delle-fonti). */
export const sourceCredentialHandlers = [
  http.get('*/source-credentials', ({ request }) =>
    withUser(request, (user) => HttpResponse.json(fakeSourceCredentials.summariesOf(user.account))),
  ),
  http.put('*/source-credentials/:adapter', ({ request, params }) =>
    withUser(request, async (user) => {
      const name = String(params.adapter);
      const { fields, within } = await textFieldsWithin(request, 'values');
      const offered = fakeSourceCredentials
        .sources()
        .flatMap((source) => source.adapters)
        .find((adapter) => adapter.name === name);
      if (offered === undefined) {
        return problem(404, 'Not Found', `adapter della fonte non disponibile: ${name}`);
      }
      if (offered.configuration_fields.length === 0) {
        return problem(
          422,
          'Unprocessable Content',
          `l'adapter ${name} non richiede configurazione`,
        );
      }
      const refusal = refusalOfValues(offered.configuration_fields, within);
      if (refusal !== undefined) {
        return refusal;
      }
      fakeSourceCredentials.save(
        user.account,
        offered,
        within,
        new Date().toISOString(),
        enteredExpiryOf(fields.expires_on),
      );
      return new HttpResponse(null, { status: 204 });
    }),
  ),
  http.put('*/source-credentials/:adapter/expiry', ({ request, params }) =>
    withUser(request, async (user) => {
      const name = String(params.adapter);
      const { expires_on } = await textFieldsOf(request);
      const credentials = fakeSourceCredentials.of(user.account, name);
      if (credentials === undefined) {
        return notFound(name);
      }
      credentials.expiry = enteredExpiryOf(expires_on);
      return new HttpResponse(null, { status: 204 });
    }),
  ),
  http.delete('*/source-credentials/:adapter', ({ request, params }) =>
    withUser(request, (user) => {
      const name = String(params.adapter);
      return fakeSourceCredentials.remove(user.account, name)
        ? new HttpResponse(null, { status: 204 })
        : notFound(name);
    }),
  ),
];
