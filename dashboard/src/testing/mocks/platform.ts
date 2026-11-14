import type { FakeCycle } from './cycles';
// The closed positions as the API lists them; FakeClosedPosition here is the history the statistics read (R2.2.6).
import type { FakeClosedPosition as ClosedPositionAnswer, FakeOpenPosition } from './positions';

/**
 * The platform behind the fakes: the users of the identity provider, their role, the accounts and the flows of their
 * tenant, the cycles and the open and closed positions of each flow and the Telegram chats. Unit tests and scenarios
 * prepare it; the fake identity provider and the fake API read it. The commands follow the rules of the API, so the
 * dashboard meets the same refusals (R2.4.1, ADR 0124).
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

export type FakeConfiguration = {
  readonly assets: string[];
  readonly cycleMinutes: number;
  readonly model: string;
  readonly instructions: string;
  readonly maxLeverage: number;
  readonly allocatedCapital: string;
};

export type FakeVersion = {
  readonly number: number;
  readonly createdAt: string;
  readonly configuration: FakeConfiguration;
};

export type FakeSource = { readonly name: string; readonly weight: number };

export type FakeFlow = {
  readonly id: string;
  name: string;
  status: string;
  accountId: string | null;
  version: number;
  assets: string[];
  allocatedCapital: number | null;
  model: string;
  sources: FakeSource[];
  cycleMinutes: number;
  /** How many cycles the worker ran for the flow since the scenario started it (R2.4.1). */
  cycles: number;
  readonly history: FakeFlowHistory;
  /** The equity every cycle of the flow recorded, in the order the scenario records it. */
  readonly equity: FakeEquityPoint[];
  readonly versions: FakeVersion[];
};

export type FakeAccount = { readonly id: string; readonly name: string; readonly balance: number };

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
  readonly accounts: FakeAccount[];
};

export type FlowOptions = Partial<Omit<FakeFlow, 'id' | 'name' | 'accountId'>> & {
  readonly accountName?: string;
};

export type Assignment = {
  readonly accountId: string;
  readonly allocatedCapital: number;
  readonly assets: string[];
};

/** A refusal of the fake API, with the status and the reason the API would answer. */
export class FakeRefusal extends Error {
  readonly status: number;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
  }
}

const TOKEN_PREFIX = 'fake-access-token-';
const DRAFT = 'bozza';
const STOPPED = 'fermo';
const ACTIVE = 'attivo';
const ARCHIVED = 'archiviato';
const TRADABLE_ASSETS = new Set(['BTC', 'ETH', 'SOL']);

export const FIRST_CONFIGURATION: FakeConfiguration = {
  assets: ['BTC'],
  cycleMinutes: 15,
  model: 'openai/gpt-4o',
  instructions: '',
  maxLeverage: 3,
  allocatedCapital: '100',
};

const FIRST_CREATION = Date.UTC(2026, 10, 1, 9, 30);
const DAY = 24 * 60 * 60 * 1000;

/** The versions of a flow, one a day from the first of November 2026, each with its changes to the one before. */
export const versionsWith = (...changes: Partial<FakeConfiguration>[]): FakeVersion[] =>
  changes.reduce<FakeVersion[]>((versions, change, index) => {
    const previous = versions.at(-1)?.configuration ?? FIRST_CONFIGURATION;
    return [
      ...versions,
      {
        number: index + 1,
        createdAt: new Date(FIRST_CREATION + index * DAY).toISOString(),
        configuration: { ...previous, ...change },
      },
    ];
  }, []);

const state = {
  users: new Map<string, FakeUser>(),
  chats: new Map<string, FakeChat>(),
  linkedChats: new Map<string, FakeChat>(),
  linkCodes: new Map<string, FakeLinkCode>(),
  cycles: new Map<string, FakeCycle[]>(),
  openPositions: new Map<string, FakeOpenPosition[]>(),
  closedPositions: new Map<string, ClosedPositionAnswer[]>(),
  signingIn: undefined as string | undefined,
  sessionsExpired: false,
  exchangeReachable: true,
};

const flowIdOf = (name: string): string => `flow-${name}`;

export const accessTokenOf = (account: string): string => `${TOKEN_PREFIX}${account}`;

const userNamed = (account: string): FakeUser => {
  const user = state.users.get(account);
  if (user === undefined) {
    throw new Error(`unknown fake user ${account}`);
  }
  return user;
};

const accountOf = (user: FakeUser, name: string): FakeAccount => {
  const existing = user.accounts.find((account) => account.name === name);
  if (existing !== undefined) {
    return existing;
  }
  const account = { id: `account-${name}`, name, balance: 1000 };
  user.accounts.push(account);
  return account;
};

const flowOf = (user: FakeUser, flowId: string): FakeFlow => {
  const flow = user.flows.find((candidate) => candidate.id === flowId);
  if (flow === undefined) {
    throw new FakeRefusal(404, 'flusso non trovato');
  }
  return flow;
};

const holdsAccount = (flow: FakeFlow) => flow.status !== DRAFT && flow.status !== ARCHIVED;

// The capital the flows of the account hold, neither draft nor archived, as the API sums it (R1.1.1, ADR 0124).
const allocatedCapital = (user: FakeUser, account: FakeAccount): number =>
  user.flows
    .filter((flow) => flow.accountId === account.id && holdsAccount(flow))
    .reduce((total, flow) => total + (flow.allocatedCapital ?? 0), 0);

const freeCapital = (user: FakeUser, account: FakeAccount): number =>
  account.balance - allocatedCapital(user, account);

const missingOf = (flow: FakeFlow): string[] =>
  [
    flow.accountId === null ? 'conto' : '',
    flow.allocatedCapital === null ? 'capitale allocato' : '',
    flow.assets.length === 0 ? 'asset' : '',
  ].filter((part) => part !== '');

const listed = (parts: string[]): string =>
  parts.length === 1
    ? `${parts[0]} mancante`
    : `${parts.slice(0, -1).join(', ')} e ${parts[parts.length - 1]} mancanti`;

const holderOf = (user: FakeUser, flow: FakeFlow): FakeFlow | undefined =>
  user.flows.find(
    (other) =>
      other.id !== flow.id &&
      other.accountId === flow.accountId &&
      holdsAccount(other) &&
      other.assets.some((asset) => flow.assets.includes(asset)),
  );

export const fakePlatform = {
  reset(): void {
    state.users.clear();
    state.chats.clear();
    state.linkedChats.clear();
    state.linkCodes.clear();
    state.cycles.clear();
    state.openPositions.clear();
    state.closedPositions.clear();
    state.signingIn = undefined;
    state.sessionsExpired = false;
    state.exchangeReachable = true;
  },

  addUser(account: string, { hasUserRole }: { hasUserRole: boolean }): void {
    state.users.set(account, {
      account,
      hasUserRole,
      tenantId: `tenant-${account}`,
      flows: [],
      accounts: [],
    });
  },

  hasUser(account: string): boolean {
    return state.users.has(account);
  },

  user(account: string): FakeUser {
    return userNamed(account);
  },

  addAccount(account: string, name: string): FakeAccount {
    return accountOf(userNamed(account), name);
  },

  addFlow(account: string, name: string, options: FlowOptions = {}): FakeFlow {
    const user = userNamed(account);
    const { accountName = 'principale', ...rest } = options;
    const flow: FakeFlow = {
      id: flowIdOf(name),
      name,
      status: ACTIVE,
      accountId: accountOf(user, accountName).id,
      version: rest.versions?.at(-1)?.number ?? 1,
      assets: ['BTC'],
      allocatedCapital: 100,
      model: 'openai/gpt-4o',
      sources: [],
      cycleMinutes: 15,
      cycles: 0,
      history: emptyHistory(),
      equity: [],
      versions: versionsWith({}),
      ...rest,
    };
    user.flows.push(flow);
    return flow;
  },

  /** The account belongs to the user, who has the Utente role: the user is created when missing. */
  giveAccountTo(account: string, name: string, balance: number): FakeAccount {
    if (!state.users.has(account)) {
      this.addUser(account, { hasUserRole: true });
    }
    const created = { id: `account-${name}`, name, balance };
    userNamed(account).accounts.push(created);
    return created;
  },

  allocatedCapitalOf(user: FakeUser, account: FakeAccount): number {
    return allocatedCapital(user, account);
  },

  freeCapitalOfAccount(user: FakeUser, account: FakeAccount): number {
    return freeCapital(user, account);
  },

  /** From now on the exchange does not answer: what the API reads from it fails as on the API. */
  stopExchange(): void {
    state.exchangeReachable = false;
  },

  exchangeReachable(): boolean {
    return state.exchangeReachable;
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

  /** The positions the flow with the name holds now on the exchange. */
  holdPositions(flowName: string, positions: FakeOpenPosition[]): void {
    state.openPositions.set(flowIdOf(flowName), positions);
  },

  openPositionsOf(flowId: string): FakeOpenPosition[] {
    return state.openPositions.get(flowId) ?? [];
  },

  /** The positions the flow with the name closed, in any order: the fake API serves them from the most recent. */
  recordClosedPositions(flowName: string, positions: ClosedPositionAnswer[]): void {
    state.closedPositions.set(flowIdOf(flowName), positions);
  },

  closedPositionsOf(flowId: string): ClosedPositionAnswer[] {
    return state.closedPositions.get(flowId) ?? [];
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

  accountNamed(name: string): FakeAccount {
    const account = [...state.users.values()]
      .flatMap((user) => user.accounts)
      .find((candidate) => candidate.name === name);
    if (account === undefined) {
      throw new Error(`unknown fake account ${name}`);
    }
    return account;
  },

  duplicate(user: FakeUser, flowId: string): FakeFlow {
    const original = flowOf(user, flowId);
    const name = `${original.name} (copia)`;
    if (user.flows.some((flow) => flow.name === name && flow.status !== ARCHIVED)) {
      throw new FakeRefusal(409, 'nome già usato da un altro flusso');
    }
    const copy: FakeFlow = {
      ...original,
      id: flowIdOf(name),
      name,
      status: DRAFT,
      accountId: null,
      version: 1,
      assets: [],
      allocatedCapital: null,
      sources: [...original.sources],
      cycles: 0,
      history: emptyHistory(),
      equity: [],
      versions: versionsWith({}),
    };
    user.flows.push(copy);
    return copy;
  },

  assign(user: FakeUser, flowId: string, assignment: Assignment): FakeFlow {
    const flow = flowOf(user, flowId);
    if (flow.status !== DRAFT) {
      throw new FakeRefusal(409, 'conto, capitale e asset si assegnano solo a un flusso in bozza');
    }
    const assets = [
      ...new Set(assignment.assets.map((asset) => asset.trim().toUpperCase()).filter(Boolean)),
    ];
    if (assets.length === 0) {
      throw new FakeRefusal(422, 'almeno un asset è obbligatorio');
    }
    const account = user.accounts.find((candidate) => candidate.id === assignment.accountId);
    if (account === undefined) {
      throw new FakeRefusal(404, 'conto non trovato');
    }
    const refused = assets.filter((asset) => !TRADABLE_ASSETS.has(asset));
    if (refused.length > 0) {
      throw new FakeRefusal(422, `asset non negoziabile sull'exchange: ${refused.join(', ')}`);
    }
    const free = freeCapital(user, account);
    if (assignment.allocatedCapital > free) {
      throw new FakeRefusal(422, `capitale allocato oltre il capitale libero: ${free} USDC`);
    }
    flow.accountId = account.id;
    flow.allocatedCapital = assignment.allocatedCapital;
    flow.assets = assets;
    flow.version += 1;
    return flow;
  },

  start(user: FakeUser, flowId: string): FakeFlow {
    const flow = flowOf(user, flowId);
    if (flow.status !== DRAFT && flow.status !== STOPPED) {
      throw new FakeRefusal(409, `comando avvia non ammesso per un flusso ${flow.status}`);
    }
    const missing = missingOf(flow);
    if (missing.length > 0) {
      throw new FakeRefusal(409, listed(missing));
    }
    const holder = holderOf(user, flow);
    if (holder !== undefined) {
      const shared = flow.assets.filter((asset) => holder.assets.includes(asset));
      throw new FakeRefusal(
        409,
        `asset già assegnati al flusso ${holder.name} sullo stesso conto: ${shared.join(', ')}`,
      );
    }
    flow.status = ACTIVE;
    return flow;
  },

  /** Time passes for the worker: every active flow runs one cycle per interval of its own. */
  passMinutes(minutes: number): void {
    for (const flow of [...state.users.values()].flatMap((user) => user.flows)) {
      if (flow.status === ACTIVE) {
        flow.cycles += Math.floor(minutes / flow.cycleMinutes);
      }
    }
  },

  freeCapitalOf(account: string, accountName: string): number {
    const user = userNamed(account);
    return freeCapital(user, accountOf(user, accountName));
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
