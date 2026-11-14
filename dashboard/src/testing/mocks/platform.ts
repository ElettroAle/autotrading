import type { FakeCycle } from './cycles';

/**
 * The platform behind the fakes: the users of the identity provider, their role, the flows of their tenant and the
 * cycles of each flow and the Telegram chats. Unit tests and scenarios prepare it; the fake identity provider and
 * the fake API read it.
 */
/** A position the flow closed: its result after the fees, the fees and the instant of the closing. */
export type FakeClosedPosition = {
  readonly netPnl: number;
  readonly fees: number;
  readonly closedAt: Date;
};

/** A call of the flow to the model: its cost in USD and the instant of its cycle. */
export type FakeModelCall = { readonly costUsd: number; readonly plannedAt: Date };

/** What a flow did: the positions it closed and the calls it made to the model. */
export type FakeFlowHistory = {
  readonly closedPositions: FakeClosedPosition[];
  readonly modelCalls: FakeModelCall[];
};

export type FakeEquityPoint = { readonly plannedAt: Date; readonly equity: number };

export type FakeFlow = {
  readonly id: string;
  readonly name: string;
  readonly status: string;
  readonly history: FakeFlowHistory;
  readonly initialCapital: string;
  /** The equity every cycle of the flow recorded, in the order the scenario records it. */
  readonly equity: FakeEquityPoint[];
};

export const emptyHistory = (): FakeFlowHistory => ({ closedPositions: [], modelCalls: [] });

/** A Telegram chat: Telegram numbers it, the scenarios name it, and it keeps what it received. */
export type FakeChat = { readonly name: string; readonly id: number; readonly received: string[] };

export type FakeLinkCode = {
  readonly code: string;
  readonly expiresAt: string;
  readonly link: string;
};

export const FAKE_LINK_CODE = 'K7M2Q9XA';
export const FAKE_BOT_LINK = 'https://t.me/autotrading_bot?start=';
const LINK_CODE_MINUTES = 15;
const FIRST_CHAT_ID = 1001;

export type FakeUser = {
  readonly account: string;
  readonly hasUserRole: boolean;
  readonly tenantId: string;
  readonly flows: FakeFlow[];
};

const TOKEN_PREFIX = 'fake-access-token-';

const state = {
  users: new Map<string, FakeUser>(),
  chats: new Map<string, FakeChat>(),
  linkedChats: new Map<string, FakeChat>(),
  linkCodes: new Map<string, FakeLinkCode>(),
  cycles: new Map<string, FakeCycle[]>(),
  signingIn: undefined as string | undefined,
  sessionsExpired: false,
};

const flowIdOf = (name: string): string => `flow-${name}`;

export const accessTokenOf = (account: string): string => `${TOKEN_PREFIX}${account}`;

export const fakePlatform = {
  reset(): void {
    state.users.clear();
    state.chats.clear();
    state.linkedChats.clear();
    state.linkCodes.clear();
    state.cycles.clear();
    state.signingIn = undefined;
    state.sessionsExpired = false;
  },

  addUser(account: string, { hasUserRole }: { hasUserRole: boolean }): void {
    state.users.set(account, { account, hasUserRole, tenantId: `tenant-${account}`, flows: [] });
  },

  hasUser(account: string): boolean {
    return state.users.has(account);
  },

  addFlow(
    account: string,
    name: string,
    history: FakeFlowHistory = emptyHistory(),
    { initialCapital = '100' }: { initialCapital?: string } = {},
  ): FakeFlow {
    const user = state.users.get(account);
    if (user === undefined) {
      throw new Error(`unknown fake user ${account}`);
    }
    const flow = {
      id: flowIdOf(name),
      name,
      status: 'attivo',
      history,
      initialCapital,
      equity: [],
    };
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

  /** The equity a cycle of the flow recorded at its planned instant (R2.2.3). */
  recordEquity(name: string, plannedAt: Date, equity: number): void {
    fakePlatform.flowNamed(name).equity.push({ plannedAt, equity });
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

  /** The chat with the name, as Telegram knows it: the same name is always the same chat. */
  chatNamed(name: string): FakeChat {
    const known = state.chats.get(name);
    if (known !== undefined) {
      return known;
    }
    const chat = { name, id: FIRST_CHAT_ID + state.chats.size, received: [] };
    state.chats.set(name, chat);
    return chat;
  },

  /** What the bot does once the chat sends it a valid code of the user (R1.8.1). */
  linkChat(account: string, chatName: string): void {
    state.linkedChats.set(account, fakePlatform.chatNamed(chatName));
  },

  linkedChatOf(account: string): FakeChat | undefined {
    return state.linkedChats.get(account);
  },

  unlinkChat(account: string): boolean {
    return state.linkedChats.delete(account);
  },

  issueLinkCode(account: string, now: Date): FakeLinkCode {
    const expiresAt = new Date(now.getTime() + LINK_CODE_MINUTES * 60_000).toISOString();
    const issued = { code: FAKE_LINK_CODE, expiresAt, link: `${FAKE_BOT_LINK}${FAKE_LINK_CODE}` };
    state.linkCodes.set(account, issued);
    return issued;
  },

  linkCodeOf(account: string): FakeLinkCode | undefined {
    return state.linkCodes.get(account);
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
