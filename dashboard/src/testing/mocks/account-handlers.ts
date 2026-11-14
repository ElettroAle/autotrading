import { http, HttpResponse } from 'msw';

import {
  EXCHANGE_REFUSAL,
  FAKE_EXCHANGE,
  REJECTED_SECRET_KEY,
  fakePlatform,
  type FakeAccount,
  type FakeUser,
} from './platform';
import { problem, textFieldsOf, withUser } from './responses';

const CURRENCY = 'USDC';

// The reasons the API gives, with the same words (R0.2.1, R0.2.4, R0.2.5, R1.1.8).
const NOT_FOUND = 'non trovato';
const CREDENTIALS_REQUIRED = 'credenziali obbligatorio';

const accountResponse = (user: FakeUser, account: FakeAccount) => ({
  id: account.id,
  name: account.name,
  exchange: 'Hyperliquid',
  has_credentials: true,
  network: 'test',
  allocated_capital: String(fakePlatform.allocatedCapitalOf(user, account)),
  currency: CURRENCY,
});

const amountOf = (amount: string) => ({ amount, currency: CURRENCY });

const accountStateResponse = (account: FakeAccount) => ({
  balance: amountOf(String(account.balance)),
  available_margin: amountOf(String(account.balance)),
  positions: [],
  read_at: '2026-11-14T09:00:00+00:00',
});

const freeCapitalResponse = (user: FakeUser, account: FakeAccount) =>
  amountOf(String(fakePlatform.freeCapitalOfAccount(user, account)));

// An account of another tenant does not exist for the user; what comes from the exchange fails when it does not answer.
const withAccountOnExchange = (
  user: FakeUser,
  accountId: string,
  respond: (account: FakeAccount) => Response,
): Response => {
  const account = user.accounts.find((candidate) => candidate.id === accountId);
  if (account === undefined) {
    return problem(404, 'Not Found', 'non trovato');
  }
  if (!fakePlatform.exchangeReachable()) {
    return problem(503, 'Service Unavailable', 'exchange non raggiungibile, riprovare');
  }
  return respond(account);
};

// The exchange reads the balance with the credentials before they are saved: a refused key saves nothing.
const refusalOfCredentials = (address: string, secretKey: string): Response | undefined => {
  if (address.trim() === '' || secretKey.trim() === '') {
    return problem(422, 'Unprocessable Content', CREDENTIALS_REQUIRED);
  }
  if (secretKey === REJECTED_SECRET_KEY) {
    return problem(422, 'Unprocessable Content', "credenziali rifiutate dall'exchange", {
      exchange_message: EXCHANGE_REFUSAL,
    });
  }
  return undefined;
};

const refusalOfRegistration = (user: FakeUser, fields: Record<string, string>) => {
  const name = (fields.name ?? '').trim();
  const exchange = (fields.exchange ?? '').trim();
  if (name === '') {
    return problem(422, 'Unprocessable Content', 'nome obbligatorio');
  }
  if (exchange === '') {
    return problem(422, 'Unprocessable Content', 'exchange obbligatorio');
  }
  if (exchange !== FAKE_EXCHANGE) {
    return problem(422, 'Unprocessable Content', 'exchange non supportato', {
      supported: [FAKE_EXCHANGE],
    });
  }
  if (user.accounts.some((account) => account.name === name)) {
    return problem(409, 'Conflict', 'nome del conto già in uso');
  }
  return refusalOfCredentials(fields.account_address ?? '', fields.secret_key ?? '');
};

const withAccount = (
  user: FakeUser,
  accountId: string,
  respond: (account: FakeAccount) => Response,
): Response => {
  const account = user.accounts.find((candidate) => candidate.id === accountId);
  return account === undefined ? problem(404, 'Not Found', NOT_FOUND) : respond(account);
};

export const accountHandlers = [
  http.get('*/accounts', ({ request }) =>
    withUser(request, (user) =>
      HttpResponse.json(user.accounts.map((account) => accountResponse(user, account))),
    ),
  ),
  http.get('*/accounts/:accountId/state', ({ request, params }) =>
    withUser(request, (user) =>
      withAccountOnExchange(user, String(params.accountId), (account) =>
        HttpResponse.json(accountStateResponse(account)),
      ),
    ),
  ),
  http.get('*/accounts/:accountId/free-capital', ({ request, params }) =>
    withUser(request, (user) =>
      withAccountOnExchange(user, String(params.accountId), (account) =>
        HttpResponse.json(freeCapitalResponse(user, account)),
      ),
    ),
  ),
  http.post('*/accounts', ({ request }) =>
    withUser(request, async (user) => {
      const fields = await textFieldsOf(request);
      const refusal = refusalOfRegistration(user, fields);
      if (refusal !== undefined) {
        return refusal;
      }
      const account = fakePlatform.addAccount(user.account, (fields.name ?? '').trim());
      return HttpResponse.json(
        {
          id: account.id,
          name: account.name,
          exchange: FAKE_EXCHANGE,
          balance: amountOf(String(account.balance)),
        },
        { status: 201 },
      );
    }),
  ),
  http.put('*/accounts/:accountId/credentials', ({ request, params }) =>
    withUser(request, async (user) => {
      const fields = await textFieldsOf(request);
      return withAccount(
        user,
        String(params.accountId),
        (account) =>
          refusalOfCredentials(fields.account_address ?? '', fields.secret_key ?? '') ??
          HttpResponse.json(accountResponse(user, account)),
      );
    }),
  ),
  http.delete('*/accounts/:accountId', ({ request, params }) =>
    withUser(request, (user) =>
      withAccount(user, String(params.accountId), (account) => {
        const confirmed = new URL(request.url).searchParams.get('confirmed') === 'true';
        const operating = fakePlatform.operatingFlowsOf(user, account);
        if (operating.length > 0 && !confirmed) {
          return problem(
            409,
            'Conflict',
            `il conto ha flussi attivi o in pausa che verranno fermati: ${operating.join(', ')}`,
          );
        }
        user.accounts.splice(user.accounts.indexOf(account), 1);
        return new HttpResponse(null, { status: 204 });
      }),
    ),
  ),
];
