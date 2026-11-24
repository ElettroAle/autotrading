import { http, HttpResponse } from 'msw';

import { enteredExpiryOf, keyExpiryResponse, type FakeKeyExpiry } from './key-expiry';
import {
  EXCHANGE_REFUSAL,
  FAKE_EXCHANGE,
  FAKE_SUPPORTED_EXCHANGES,
  REJECTED_SECRET_KEY,
  SIMULATED_EXCHANGE,
  fakePlatform,
  type FakeAccount,
  type FakeUser,
} from './platform';
import { problem, textFieldsWithin, withUser } from './responses';

const CURRENCY = 'USDC';

// The reasons the API gives, with the same words (R0.2.1, R0.2.4, R0.2.5, R1.1.8).
const NOT_FOUND = 'non trovato';
const CREDENTIALS_REQUIRED = 'credenziali obbligatorio';

// The fields the exchange declares for its credentials (R2.3.9, ADR 0158).
const CREDENTIAL_FIELDS = [
  { name: 'account_address', label: 'Indirizzo del conto', secret: false },
  { name: 'secret_key', label: "Chiave dell'API wallet", secret: true },
] as const;

// The simulated exchange trades no money and names its own network (R6.3.2).
const SIMULATED_NETWORK = { network: 'test', network_name: SIMULATED_EXCHANGE } as const;

const isSimulated = (account: FakeAccount): boolean => account.exchange === SIMULATED_EXCHANGE;

const networkOf = (account: FakeAccount) =>
  isSimulated(account)
    ? SIMULATED_NETWORK
    : { network: fakePlatform.exchangeNetwork(), network_name: fakePlatform.exchangeNetworkName() };

const accountResponse = (user: FakeUser, account: FakeAccount) => ({
  id: account.id,
  name: account.name,
  exchange: account.exchange ?? FAKE_EXCHANGE,
  has_credentials: !isSimulated(account),
  public_fields: account.publicFields,
  ...networkOf(account),
  allocated_capital: String(fakePlatform.allocatedCapitalOf(user, account)),
  currency: CURRENCY,
  // The exchange of the fake platform reads the expiry of the credentials, unless a test says otherwise (R6.2.2).
  ...keyExpiryResponse(account.expiry, account.expiryEditable ?? false),
});

const EXPIRY_READ_BY_EXCHANGE = "la scadenza di queste credenziali la legge l'exchange";

const expiryRefusal = () => problem(409, 'Conflict', EXPIRY_READ_BY_EXCHANGE);

const givesExpiry = (fields: Record<string, string>): boolean => (fields.expires_on ?? '') !== '';

const amountOf = (amount: string) => ({ amount, currency: CURRENCY });

// The reasons the API gives about a virtual balance, with the same words (R6.3.2).
const VIRTUAL_BALANCE_REQUIRED = 'saldo virtuale obbligatorio per questo exchange';
const VIRTUAL_BALANCE_NOT_POSITIVE = 'il saldo virtuale deve essere maggiore di zero';
const NO_VIRTUAL_BALANCE = 'questo exchange non ha un saldo virtuale';

const noVirtualBalance = () => problem(409, 'Conflict', NO_VIRTUAL_BALANCE);

// A positive amount, or the refusal the API answers with (R6.3.2).
const virtualBalanceOf = (text: string | undefined): number | Response => {
  if ((text ?? '').trim() === '') {
    return problem(422, 'Unprocessable Content', VIRTUAL_BALANCE_REQUIRED);
  }
  const amount = Number(text);
  return Number.isFinite(amount) && amount > 0
    ? amount
    : problem(422, 'Unprocessable Content', VIRTUAL_BALANCE_NOT_POSITIVE);
};

const simulatedExchange = () => ({
  name: SIMULATED_EXCHANGE,
  ...SIMULATED_NETWORK,
  fields: [],
  expiry_editable: false,
  virtual_balance: true,
});

const accountStateResponse = (account: FakeAccount) => ({
  balance: amountOf(String(account.balance)),
  available_margin: amountOf(String(account.balance)),
  positions: [],
  read_at: '2026-11-14T09:00:00+00:00',
});

// The flows of the fake platform earn nothing: their value is the capital allocated to them (Bug 601).
const freeCapitalResponse = (user: FakeUser, account: FakeAccount) => ({
  ...amountOf(String(fakePlatform.freeCapitalOfAccount(user, account))),
  flows_value: String(fakePlatform.allocatedCapitalOf(user, account)),
  flows_result: '0',
});

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
const refusalOfCredentials = (credentials: Record<string, string>): Response | undefined => {
  const unknown = Object.keys(credentials).find(
    (name) => !CREDENTIAL_FIELDS.some((field) => field.name === name),
  );
  if (unknown !== undefined) {
    return problem(
      422,
      'Unprocessable Content',
      `campo delle credenziali non previsto: ${unknown}`,
      {
        field: unknown,
      },
    );
  }
  if (Object.values(credentials).every((value) => value.trim() === '')) {
    return problem(422, 'Unprocessable Content', CREDENTIALS_REQUIRED);
  }
  const missing = CREDENTIAL_FIELDS.find((field) => (credentials[field.name] ?? '').trim() === '');
  if (missing !== undefined) {
    const label = `${missing.label.charAt(0).toLowerCase()}${missing.label.slice(1)}`;
    return problem(422, 'Unprocessable Content', `${label} obbligatorio`, { field: missing.name });
  }
  const secretKey = credentials.secret_key ?? '';
  if (secretKey === REJECTED_SECRET_KEY) {
    return problem(422, 'Unprocessable Content', "credenziali rifiutate dall'exchange", {
      exchange_message: EXCHANGE_REFUSAL,
    });
  }
  return undefined;
};

const publicFieldsOf = (credentials: Record<string, string>): Record<string, string> =>
  Object.fromEntries(
    CREDENTIAL_FIELDS.filter((field) => !field.secret && field.name in credentials).map((field) => [
      field.name,
      (credentials[field.name] ?? '').trim(),
    ]),
  );

// A replacement asks only the secret fields: the public ones stay those registered, unless none is kept (Bug 401).
const replacementOf = (
  user: FakeUser,
  account: FakeAccount,
  sent: Record<string, string>,
  expiry?: FakeKeyExpiry,
): Response => {
  const kept = Object.keys(account.publicFields).length > 0;
  const sentPublic = CREDENTIAL_FIELDS.find((field) => !field.secret && field.name in sent);
  if (kept && sentPublic !== undefined) {
    const label = `${sentPublic.label.charAt(0).toLowerCase()}${sentPublic.label.slice(1)}`;
    return problem(
      400,
      'Bad Request',
      `${label} non si sostituisce: per cambiarlo rimuovi il conto e registrane uno nuovo`,
      { field: sentPublic.name },
    );
  }
  const credentials = kept ? { ...account.publicFields, ...sent } : sent;
  const refusal = refusalOfCredentials(credentials);
  if (refusal !== undefined) {
    return refusal;
  }
  account.publicFields = publicFieldsOf(credentials);
  // New credentials keep only the date given with them where the user gives it (R6.2.2).
  if (account.expiryEditable === true) {
    account.expiry = expiry;
  }
  return HttpResponse.json(accountResponse(user, account));
};

const refusalOfRegistration = (
  user: FakeUser,
  fields: Record<string, string>,
  credentials: Record<string, string>,
) => {
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
  if (givesVirtualBalance(fields)) {
    return noVirtualBalance();
  }
  if (user.accounts.some((account) => account.name === name)) {
    return problem(409, 'Conflict', 'nome del conto già in uso');
  }
  return refusalOfCredentials(credentials);
};

const givesVirtualBalance = (fields: Record<string, string>): boolean =>
  (fields.virtual_balance ?? '').trim() !== '';

const registered = (account: FakeAccount) =>
  HttpResponse.json(
    {
      id: account.id,
      name: account.name,
      exchange: account.exchange ?? FAKE_EXCHANGE,
      balance: amountOf(String(account.balance)),
    },
    { status: 201 },
  );

// An account of the simulated exchange: no credentials, the virtual balance it starts from (R6.3.2).
const simulatedRegistration = (
  user: FakeUser,
  fields: Record<string, string>,
  credentials: Record<string, string>,
): Response => {
  const name = (fields.name ?? '').trim();
  const [unknown] = Object.keys(credentials);
  if (unknown !== undefined) {
    return problem(
      422,
      'Unprocessable Content',
      `campo delle credenziali non previsto: ${unknown}`,
      {
        field: unknown,
      },
    );
  }
  if (name === '') {
    return problem(422, 'Unprocessable Content', 'nome obbligatorio');
  }
  if (user.accounts.some((account) => account.name === name)) {
    return problem(409, 'Conflict', 'nome del conto già in uso');
  }
  const balance = virtualBalanceOf(fields.virtual_balance);
  if (balance instanceof Response) {
    return balance;
  }
  return registered(fakePlatform.addSimulatedAccount(user.account, name, balance));
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
  http.get('*/exchanges', ({ request }) =>
    withUser(request, () =>
      fakePlatform.listsExchanges()
        ? HttpResponse.json([
            ...FAKE_SUPPORTED_EXCHANGES.map((name) => ({
              name,
              network: fakePlatform.exchangeNetwork(),
              network_name: fakePlatform.exchangeNetworkName(),
              fields: CREDENTIAL_FIELDS,
              expiry_editable: !fakePlatform.exchangeReadsExpiry(),
              virtual_balance: false,
            })),
            ...(fakePlatform.offersSimulatedExchange() ? [simulatedExchange()] : []),
          ])
        : problem(500, 'Internal Server Error', 'errore interno'),
    ),
  ),
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
      const { fields, within } = await textFieldsWithin(request, 'credentials');
      if (fakePlatform.offersSimulatedExchange() && fields.exchange === SIMULATED_EXCHANGE) {
        return simulatedRegistration(user, fields, within);
      }
      if (givesExpiry(fields) && fakePlatform.exchangeReadsExpiry()) {
        return expiryRefusal();
      }
      const refusal = refusalOfRegistration(user, fields, within);
      if (refusal !== undefined) {
        return refusal;
      }
      const account = fakePlatform.addAccount(user.account, (fields.name ?? '').trim());
      account.publicFields = publicFieldsOf(within);
      account.expiryEditable = !fakePlatform.exchangeReadsExpiry();
      account.expiry = enteredExpiryOf(fields.expires_on);
      return registered(account);
    }),
  ),
  http.put('*/accounts/:accountId/virtual-balance', ({ request, params }) =>
    withUser(request, async (user) => {
      const { fields } = await textFieldsWithin(request, 'credentials');
      return withAccount(user, String(params.accountId), (account) => {
        if (!isSimulated(account)) {
          return noVirtualBalance();
        }
        const balance = virtualBalanceOf(fields.balance);
        if (balance instanceof Response) {
          return balance;
        }
        account.balance = balance;
        return new HttpResponse(null, { status: 204 });
      });
    }),
  ),
  http.put('*/accounts/:accountId/credentials', ({ request, params }) =>
    withUser(request, async (user) => {
      const { fields, within } = await textFieldsWithin(request, 'credentials');
      return withAccount(user, String(params.accountId), (account) =>
        givesExpiry(fields) && account.expiryEditable !== true
          ? expiryRefusal()
          : replacementOf(user, account, within, enteredExpiryOf(fields.expires_on)),
      );
    }),
  ),
  http.put('*/accounts/:accountId/expiry', ({ request, params }) =>
    withUser(request, async (user) => {
      const { fields } = await textFieldsWithin(request, 'credentials');
      return withAccount(user, String(params.accountId), (account) => {
        if (account.expiryEditable !== true) {
          return expiryRefusal();
        }
        account.expiry = enteredExpiryOf(fields.expires_on);
        return new HttpResponse(null, { status: 204 });
      });
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
