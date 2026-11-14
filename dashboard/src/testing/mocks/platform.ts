import type { FakeCycle } from './cycles';
// The closed positions as the API lists them; FakeClosedPosition here is the history the statistics read (R2.2.6).
import { emptyRecords, type FakeRecords } from './history';
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

export type FakeSource = {
  readonly name: string;
  readonly weight: number;
  readonly parameters?: Readonly<Record<string, number>>;
};

/** The risk rules of a flow, as the API names them (R1.1.3). */
export type FakeRiskLimits = {
  readonly maxLeverage: number;
  readonly maxMarginExposurePercent: string | null;
  readonly maxValueExposurePercent: string | null;
};

export type FakeFlow = {
  readonly id: string;
  name: string;
  status: string;
  accountId: string | null;
  version: number;
  assets: string[];
  allocatedCapital: number | null;
  model: string;
  modelParameters: Record<string, string>;
  sources: FakeSource[];
  cycleMinutes: number;
  instructions: string;
  riskLimits: FakeRiskLimits;
  bringToMinimum: boolean;
  /** How many cycles the worker ran for the flow since the scenario started it (R2.4.1). */
  cycles: number;
  /** Why the flow paused, as the API says it (R1.2.4). */
  pauseReason: string | null;
  /** What the flow is worth now, as the API measures it (R2.2.2). */
  currentCapital: number;
  readonly history: FakeFlowHistory;
  /** The equity every cycle of the flow recorded, in the order the scenario records it. */
  readonly equity: FakeEquityPoint[];
  readonly versions: FakeVersion[];
};

export type FakeAccount = { readonly id: string; readonly name: string; readonly balance: number };

/** What a scenario or a test changes of a flow: its status, why it paused and its capital. */
export type FakeFlowChanges = Partial<Omit<FakeFlow, 'id' | 'name'>>;

/** The configuration version in force of a flow, as the API answers it. */
export type FakeFlowConfiguration = {
  account_id: string | null;
  version: number;
  assets: string[];
  cycle_minutes: number;
  model: { name: string; parameters: Record<string, string> };
  sources: { name: string; weight: number; parameters: Readonly<Record<string, number>> }[];
  instructions: string;
  risk_limits: {
    max_leverage: number;
    max_margin_exposure_percent: string | null;
    max_value_exposure_percent: string | null;
  };
  allocated_capital: string | null;
  bring_to_minimum: boolean;
};

/** The configuration of the flow in force, in the shape of the answers of the API. */
export const configurationOf = (flow: FakeFlow): FakeFlowConfiguration => ({
  account_id: flow.accountId,
  version: flow.version,
  assets: flow.assets,
  cycle_minutes: flow.cycleMinutes,
  model: { name: flow.model, parameters: flow.modelParameters },
  sources: flow.sources.map((source) => ({ parameters: {}, ...source })),
  instructions: flow.instructions,
  risk_limits: {
    max_leverage: flow.riskLimits.maxLeverage,
    max_margin_exposure_percent: flow.riskLimits.maxMarginExposurePercent,
    max_value_exposure_percent: flow.riskLimits.maxValueExposurePercent,
  },
  allocated_capital: flow.allocatedCapital === null ? null : String(flow.allocatedCapital),
  bring_to_minimum: flow.bringToMinimum,
});

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

/** The key of a provider of models, as the API shows it: the provider and when the key was saved, never the key. */
export type FakeProviderKey = { readonly provider: string; registeredAt: string };

export const FAKE_EXCHANGE = 'hyperliquid';
/** The secret key the exchange refuses, with the message it answers. */
export const REJECTED_SECRET_KEY = '0xrifiutata';
export const EXCHANGE_REFUSAL = 'User or API Wallet does not exist';

export type FakeUser = {
  readonly account: string;
  readonly hasUserRole: boolean;
  readonly tenantId: string;
  readonly flows: FakeFlow[];
  readonly accounts: FakeAccount[];
  readonly records: FakeRecords;
  readonly providerKeys: FakeProviderKey[];
};

export type FlowOptions = Partial<Omit<FakeFlow, 'id' | 'name' | 'accountId'>> & {
  readonly accountName?: string;
};

export type Assignment = {
  readonly accountId: string;
  readonly allocatedCapital: number;
  readonly assets: string[];
};

/** The strategy file of a flow, as the API writes it: no account, capital, assets or keys (R2.5.2, ADR 0140). */
export type FakeStrategyDocument = {
  readonly format: string;
  readonly format_version: number;
  readonly strategy: {
    readonly cycle_minutes?: number;
    readonly model?: { readonly name: string; readonly parameters: Record<string, string> };
    readonly sources?: { readonly name: string; readonly weight: number }[];
    readonly instructions?: string;
    readonly risk_limits?: Record<string, number | string | null>;
    readonly bring_to_minimum?: boolean;
  };
};

export const STRATEGY_FORMAT = 'autotrading-strategy';

/** The models the catalog of the fake platform offers: any other model is not available (R1.4.2). */
export const FAKE_MODEL_CATALOG = new Set([
  'openai/gpt-4o',
  'openrouter/deepseek-chat',
  'anthropic/claude-sonnet',
]);

/** A refusal of the fake API, with the status and the reason the API would answer. */
export class FakeRefusal extends Error {
  readonly status: number;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
  }
}

/** The commands of the API on a flow besides the start, as their paths name them (R1.1.4-R1.1.6). */
export const FAKE_FLOW_COMMANDS = ['pause', 'resume', 'stop', 'archive'] as const;

export type FakeFlowCommand = (typeof FAKE_FLOW_COMMANDS)[number];

type Transition = {
  readonly from: readonly string[];
  readonly to: string;
  readonly refusal: (status: string) => string;
};

const refusedFor =
  (name: string) =>
  (status: string): string =>
    `comando ${name} non ammesso per un flusso ${status}`;

const TOKEN_PREFIX = 'fake-access-token-';

export const DEFAULT_RISK_LIMITS: FakeRiskLimits = {
  maxLeverage: 3,
  maxMarginExposurePercent: '10',
  maxValueExposurePercent: null,
};
const DRAFT = 'bozza';
const STOPPED = 'fermo';
const ACTIVE = 'attivo';
const ARCHIVED = 'archiviato';
const PAUSED = 'in pausa';

// The transitions of the domain of the API, with the reasons it gives (R1.1.4-R1.1.6).
const TRANSITIONS: Record<FakeFlowCommand, Transition> = {
  pause: { from: [ACTIVE], to: PAUSED, refusal: refusedFor('pausa') },
  resume: { from: [PAUSED], to: ACTIVE, refusal: refusedFor('riprendi') },
  stop: { from: [ACTIVE, PAUSED], to: STOPPED, refusal: refusedFor('ferma') },
  archive: { from: [STOPPED], to: ARCHIVED, refusal: () => 'si archivia solo un flusso fermo' },
};
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

export const flowIdOf = (name: string): string => `flow-${name}`;

const userNamed = (account: string): FakeUser => {
  const user = state.users.get(account);
  if (user === undefined) {
    throw new Error(`unknown fake user ${account}`);
  }
  return user;
};

export const accessTokenOf = (account: string): string => `${TOKEN_PREFIX}${account}`;

const accountOf = (user: FakeUser, name: string): FakeAccount => {
  const existing = user.accounts.find((account) => account.name === name);
  if (existing !== undefined) {
    return existing;
  }
  const account = { id: `account-${name}`, name, balance: 1000 };
  user.accounts.push(account);
  return account;
};

const requireFreeName = (user: FakeUser, name: string): void => {
  if (user.flows.some((flow) => flow.name === name && flow.status !== ARCHIVED)) {
    throw new FakeRefusal(409, 'nome già usato da un altro flusso');
  }
};

/** A draft with the strategy alone, its own history from version 1 (ADR 0124). */
const draftOf = (
  name: string,
  strategy: Pick<FakeFlow, 'model' | 'sources' | 'cycleMinutes'> &
    Partial<Pick<FakeFlow, 'modelParameters' | 'instructions' | 'riskLimits' | 'bringToMinimum'>>,
): FakeFlow => ({
  id: flowIdOf(name),
  name,
  status: DRAFT,
  accountId: null,
  version: 1,
  assets: [],
  allocatedCapital: null,
  model: strategy.model,
  modelParameters: { ...strategy.modelParameters },
  sources: strategy.sources.map((source) => ({ ...source })),
  cycleMinutes: strategy.cycleMinutes,
  instructions: strategy.instructions ?? '',
  riskLimits: strategy.riskLimits ?? DEFAULT_RISK_LIMITS,
  bringToMinimum: strategy.bringToMinimum ?? false,
  cycles: 0,
  pauseReason: null,
  currentCapital: 0,
  history: emptyHistory(),
  equity: [],
  versions: versionsWith({}),
});

const modelOfStrategy = (document: FakeStrategyDocument): string => {
  if (document.format !== STRATEGY_FORMAT || document.format_version !== 1) {
    throw new FakeRefusal(
      400,
      `formato del file non supportato: ${document.format} versione ${document.format_version}`,
    );
  }
  const model = document.strategy.model?.name.trim() ?? '';
  if (model === '') {
    throw new FakeRefusal(422, 'modello mancante');
  }
  if (!FAKE_MODEL_CATALOG.has(model)) {
    throw new FakeRefusal(422, `modello non disponibile: ${model}`);
  }
  return model;
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

// Bug 244: a stopped flow starts only if its capital fits in what the other flows of its account leave free.
const requireFreeCapitalFor = (user: FakeUser, flow: FakeFlow): void => {
  const account = user.accounts.find((candidate) => candidate.id === flow.accountId);
  if (account === undefined) {
    return;
  }
  const own = holdsAccount(flow) ? (flow.allocatedCapital ?? 0) : 0;
  const free = freeCapital(user, account) + own;
  if ((flow.allocatedCapital ?? 0) > free) {
    throw new FakeRefusal(422, `capitale allocato oltre il capitale libero: ${free} USDC`);
  }
};

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
      records: emptyRecords(),
      providerKeys: [],
    });
  },

  /** The key of the user for the provider, saved at the instant: a new instant on every replacement. */
  saveProviderKey(account: string, provider: string, registeredAt: string): FakeProviderKey {
    const user = userNamed(account);
    const saved = user.providerKeys.find((key) => key.provider === provider);
    if (saved !== undefined) {
      saved.registeredAt = registeredAt;
      return saved;
    }
    const created = { provider, registeredAt };
    user.providerKeys.push(created);
    return created;
  },

  providerKeyOf(account: string, provider: string): FakeProviderKey | undefined {
    return userNamed(account).providerKeys.find((key) => key.provider === provider);
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
      modelParameters: {},
      sources: [],
      cycleMinutes: 15,
      instructions: '',
      riskLimits: DEFAULT_RISK_LIMITS,
      bringToMinimum: false,
      cycles: 0,
      pauseReason: null,
      currentCapital: 100,
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

  /** The flows active or paused on the account, which its removal would stop (R1.1.8). */
  operatingFlowsOf(user: FakeUser, account: FakeAccount): string[] {
    return user.flows
      .filter(
        (flow) =>
          flow.accountId === account.id && (flow.status === ACTIVE || flow.status === PAUSED),
      )
      .map((flow) => flow.name);
  },

  /** From now on the exchange does not answer: what the API reads from it fails as on the API. */
  stopExchange(): void {
    state.exchangeReachable = false;
  },

  exchangeReachable(): boolean {
    return state.exchangeReachable;
  },

  /** A stopped flow of the user with the configuration given as the API writes it, the rest as the other flows. */
  addConfiguredFlow(
    account: string,
    name: string,
    configuration: Partial<FakeFlowConfiguration>,
  ): FakeFlow {
    const { risk_limits: limits, model } = configuration;
    const owner = userNamed(account).accounts.find(({ id }) => id === configuration.account_id);
    return this.addFlow(account, name, {
      status: STOPPED,
      ...(owner === undefined ? {} : { accountName: owner.name }),
      ...(configuration.version === undefined ? {} : { version: configuration.version }),
      ...(configuration.assets === undefined ? {} : { assets: configuration.assets }),
      ...(model === undefined ? {} : { model: model.name, modelParameters: model.parameters }),
      ...(configuration.sources === undefined ? {} : { sources: configuration.sources }),
      ...(limits === undefined
        ? {}
        : {
            riskLimits: {
              maxLeverage: limits.max_leverage,
              maxMarginExposurePercent: limits.max_margin_exposure_percent,
              maxValueExposurePercent: limits.max_value_exposure_percent,
            },
          }),
      ...(configuration.allocated_capital == null
        ? {}
        : { allocatedCapital: Number(configuration.allocated_capital) }),
    });
  },

  flowsOf(account: string): FakeFlow[] {
    return userNamed(account).flows;
  },

  /** The flow belongs to the account, which has the Utente role: both are created when missing. */
  giveFlowTo(account: string, name: string): FakeFlow {
    if (!state.users.has(account)) {
      this.addUser(account, { hasUserRole: true });
    }
    const owned = state.users.get(account)?.flows.find((flow) => flow.name === name);
    return owned ?? this.addFlow(account, name);
  },

  /** Changes the flow with the name wherever it is, as the platform would after a command or a cycle. */
  changeFlow(name: string, changes: FakeFlowChanges): FakeFlow {
    return Object.assign(this.flowNamed(name), changes);
  },

  /** The histories of the tenant of the user (R2.5.1): the fake API serves only these to the user. */
  recordsOf(account: string): FakeRecords {
    return userNamed(account).records;
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
    requireFreeName(user, name);
    const copy = draftOf(name, original);
    user.flows.push(copy);
    return copy;
  },

  /** The strategy file of the flow, as the API exports it, and the name of the flow that names it (R2.5.2). */
  exportStrategy(
    user: FakeUser,
    flowId: string,
  ): { readonly flowName: string; readonly document: FakeStrategyDocument } {
    const flow = flowOf(user, flowId);
    const document: FakeStrategyDocument = {
      format: STRATEGY_FORMAT,
      format_version: 1,
      strategy: {
        cycle_minutes: flow.cycleMinutes,
        model: { name: flow.model, parameters: {} },
        sources: flow.sources.map((source) => ({ ...source, parameters: {} })),
        instructions: '',
        risk_limits: {
          max_leverage: 3,
          max_margin_exposure_percent: '10',
          max_value_exposure_percent: null,
        },
        bring_to_minimum: false,
      },
    };
    return { flowName: flow.name, document };
  },

  /** A draft with the strategy of the file, refused with the reason the API gives when the file is not valid. */
  importStrategy(user: FakeUser, name: string, document: FakeStrategyDocument): FakeFlow {
    const flowName = name.trim();
    if (flowName === '') {
      throw new FakeRefusal(422, 'nome del flusso obbligatorio');
    }
    requireFreeName(user, flowName);
    const draft = draftOf(flowName, {
      model: modelOfStrategy(document),
      sources: (document.strategy.sources ?? []).map(({ name, weight }) => ({ name, weight })),
      cycleMinutes: document.strategy.cycle_minutes ?? 15,
    });
    user.flows.push(draft);
    return draft;
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
    requireFreeCapitalFor(user, flow);
    flow.status = ACTIVE;
    return flow;
  },

  /** A command of the user on the flow, refused as the API refuses it; the stop closes every position (R1.1.4-R1.1.6). */
  command(user: FakeUser, flowId: string, command: FakeFlowCommand): FakeFlow {
    const flow = flowOf(user, flowId);
    const transition = TRANSITIONS[command];
    if (!transition.from.includes(flow.status)) {
      throw new FakeRefusal(409, transition.refusal(flow.status));
    }
    if (command === 'stop') {
      state.openPositions.delete(flow.id);
    }
    flow.status = transition.to;
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
