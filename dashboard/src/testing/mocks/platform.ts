/**
 * The platform behind the fakes: the users of the identity provider, their role and the flows of their tenant.
 * Unit tests and scenarios prepare it; the fake identity provider and the fake API read it.
 */
export type FakeFlow = { readonly id: string; readonly name: string; readonly status: string };

export type FakeUser = {
  readonly account: string;
  readonly hasUserRole: boolean;
  readonly tenantId: string;
  readonly flows: FakeFlow[];
};

const TOKEN_PREFIX = 'fake-access-token-';

const state = {
  users: new Map<string, FakeUser>(),
  signingIn: undefined as string | undefined,
  sessionsExpired: false,
};

export const accessTokenOf = (account: string): string => `${TOKEN_PREFIX}${account}`;

export const fakePlatform = {
  reset(): void {
    state.users.clear();
    state.signingIn = undefined;
    state.sessionsExpired = false;
  },

  addUser(account: string, { hasUserRole }: { hasUserRole: boolean }): void {
    state.users.set(account, { account, hasUserRole, tenantId: `tenant-${account}`, flows: [] });
  },

  addFlow(account: string, name: string): FakeFlow {
    const user = state.users.get(account);
    if (user === undefined) {
      throw new Error(`unknown fake user ${account}`);
    }
    const flow = { id: `flow-${name}`, name, status: 'attivo' };
    user.flows.push(flow);
    return flow;
  },

  flowNamed(name: string): FakeFlow {
    const flow = [...state.users.values()]
      .flatMap((user) => user.flows)
      .find((candidate) => candidate.name === name);
    if (flow === undefined) {
      throw new Error(`unknown fake flow ${name}`);
    }
    return flow;
  },

  userOfToken(token: string): FakeUser | undefined {
    return token.startsWith(TOKEN_PREFIX)
      ? state.users.get(token.slice(TOKEN_PREFIX.length))
      : undefined;
  },

  /** The account the user types on the sign-in page of the identity provider. */
  signIn(account: string): void {
    state.signingIn = account;
  },

  signingInAccount(): string | undefined {
    return state.signingIn;
  },

  /** From now on the identity provider refuses to renew the tokens it issued: the user must sign in again. */
  expireSessions(): void {
    state.sessionsExpired = true;
  },

  restoreSessions(): void {
    state.sessionsExpired = false;
  },

  sessionsExpired(): boolean {
    return state.sessionsExpired;
  },
};
