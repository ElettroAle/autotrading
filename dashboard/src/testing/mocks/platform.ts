import type { FakeCycle } from './cycles';

/**
 * The platform behind the fakes: the users of the identity provider, their role, the flows of their tenant and the
 * cycles of each flow. Unit tests and scenarios prepare it; the fake identity provider and the fake API read it.
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
  cycles: new Map<string, FakeCycle[]>(),
  signingIn: undefined as string | undefined,
  sessionsExpired: false,
};

const flowIdOf = (name: string): string => `flow-${name}`;

export const accessTokenOf = (account: string): string => `${TOKEN_PREFIX}${account}`;

export const fakePlatform = {
  reset(): void {
    state.users.clear();
    state.cycles.clear();
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
    const flow = { id: flowIdOf(name), name, status: 'attivo' };
    user.flows.push(flow);
    return flow;
  },

  /** The flow belongs to the account, which has the Utente role: both are created when missing. */
  giveFlowTo(account: string, name: string): FakeFlow {
    if (!state.users.has(account)) {
      this.addUser(account, { hasUserRole: true });
    }
    const owned = state.users.get(account)?.flows.find((flow) => flow.name === name);
    return owned ?? this.addFlow(account, name);
  },

  /** The cycles recorded for the flow with the name, in any order: the fake API serves them from the most recent. */
  recordCycles(flowName: string, cycles: FakeCycle[]): void {
    state.cycles.set(flowIdOf(flowName), cycles);
  },

  cyclesOf(flowId: string): FakeCycle[] {
    return state.cycles.get(flowId) ?? [];
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
