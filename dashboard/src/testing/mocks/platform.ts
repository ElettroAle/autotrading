import { fakeAlerts } from './alerts';
import { FAKE_SYSTEM_PROMPT } from './catalogs';
import { fakeClock } from './clock';
import { aCompletedCycle, type FakeAssetMemory, type FakeCycle } from './cycles';
// The closed positions as the API lists them; FakeClosedPosition here is the history the statistics read (R2.2.6).
import { emptyRecords, type FakeRecords } from './history';
import type { FakeKeyExpiry } from './key-expiry';
import { fakeNotificationChannels } from './notification-channels';
import { fakeInbox } from './notification-inbox';
import type { FakeClosedPosition as ClosedPositionAnswer, FakeOpenPosition } from './positions';
import { fakeReconciliation } from './reconciliation';
import { fakeSourceCredentials } from './source-credentials';
import type { FakeParameterValue } from './source-parameters';
import { fakeSourceTrials } from './source-trials';

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

/** How suspended openings resume: by the user, or on their own at the next midnight UTC (R3.2.2). */
export type FakeOpeningsResume = 'manual' | 'next_day';

/** The openings of a flow suspended for maximum loss, as the API says it (R3.2.2). */
export type FakeOpeningsSuspension = { readonly reason: string; readonly suspendedAt: string };

/** A block of the reopenings of one side in force, as the state of the flow gives it (R5.5.2). */
export type FakeReopeningBlock = {
  readonly side: 'long' | 'short';
  readonly asset: string | null;
  readonly consecutive_losses: number;
  readonly until: string;
  readonly text: string;
};

/**
 * A price forecast the flow recorded (R1.3.5): asset, horizon, the instant it expires, the price it forecast and the
 * actual price at that instant, null when never read.
 */
export type FakeForecast = {
  readonly asset: string;
  readonly horizonMinutes: number;
  readonly expiresAt: Date;
  readonly predictedPrice: number;
  readonly actualPrice: number | null;
};

/**
 * The memory of a flow: off unless the user turns it on, with the decisions per asset and the days (R5.3.4), the length
 * of the motive, null for a whole motive, and whether it remembers every decision (R5.3.5); the summary and the
 * other assets, off unless the user turns them on (R5.3.7).
 */
export type FakeMemory = {
  readonly active: boolean;
  readonly decisions: number;
  readonly days: number;
  readonly text_length: number | null;
  readonly all_decisions: boolean;
  readonly summary: boolean;
  readonly other_assets: boolean;
};

export const DEFAULT_MEMORY: FakeMemory = {
  active: false,
  decisions: 10,
  days: 30,
  text_length: 160,
  all_decisions: false,
  summary: false,
  other_assets: false,
};

/**
 * The stop that follows the price of a flow: every part empty and the option off unless the user sets them (R5.5.1).
 */
export type FakeTrailingStop = {
  readonly distance_percent: string | null;
  readonly activation_percent: string | null;
  readonly breakeven_percent: string | null;
  readonly max_profit_in_context: boolean;
};

export const DEFAULT_TRAILING_STOP: FakeTrailingStop = {
  distance_percent: null,
  activation_percent: null,
  breakeven_percent: null,
  max_profit_in_context: false,
};

/** The block of the reopenings after consecutive losses of a flow, null unless the user sets it (R5.5.2). */
export type FakeConsecutiveLossLimit = {
  readonly max_consecutive_losses: number;
  readonly loss_window_hours: number;
  readonly block_minutes: number;
  readonly count_scope: 'asset' | 'flusso';
} | null;

export type FakeConfiguration = {
  readonly assets: string[];
  readonly cycleMinutes: number;
  readonly model: string;
  readonly instructions: string;
  readonly maxLeverage: number;
  readonly allocatedCapital: string;
  readonly systemPrompt: string | null;
  readonly maxConsecutiveFailures: number | null;
  readonly maxDailyLossPercent: string | null;
  readonly maxDrawdownPercent: string | null;
  readonly openingsResume: FakeOpeningsResume;
  readonly defaultStopLossPercent: string;
  readonly defaultTakeProfitPercent: string | null;
  readonly minimumConfidence: number | null;
  readonly memory: FakeMemory;
  readonly trailingStop: FakeTrailingStop;
  readonly consecutiveLossLimit: FakeConsecutiveLossLimit;
  readonly accountExposureForAgent: boolean;
};

export type FakeVersion = {
  readonly number: number;
  readonly createdAt: string;
  readonly configuration: FakeConfiguration;
};

/** An adapter chosen for a source of a flow, with its weight and its parameters (R4.1.1). */
export type FakeAdapterChoice = {
  readonly name: string;
  readonly weight: number;
  readonly parameters?: Readonly<Record<string, FakeParameterValue>>;
};

/** An active source of a flow with the adapters chosen (R4.1.1). */
export type FakeSource = {
  readonly name: string;
  readonly adapters: FakeAdapterChoice[];
};

const copyOf = (source: FakeSource): FakeSource => ({
  name: source.name,
  adapters: source.adapters.map((adapter) => ({ ...adapter })),
});

/** The risk rules of a flow, as the API names them (R1.1.3). */
export type FakeRiskLimits = {
  readonly maxLeverage: number;
  readonly maxMarginExposurePercent: string | null;
  readonly maxValueExposurePercent: string | null;
  /** The overall limits on the sum of the open positions; null for none (R3.2.1). */
  readonly maxTotalMarginExposurePercent: string | null;
  readonly maxTotalValueExposurePercent: string | null;
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
  /** The stop loss and take profit defaults of the flow, in percent of the entry price (R3.1.2). */
  defaultStopLossPercent: string;
  defaultTakeProfitPercent: string | null;
  /** The confidence an opening needs at least, from 0 to 100; null for none (R3.1.4). */
  minimumConfidence: number | null;
  bringToMinimum: boolean;
  /** The system prompt the user wrote; null follows the default of the platform (R1.4.8). */
  systemPrompt: string | null;
  /** The failed cycles in a row after which the flow pauses; null keeps it trying (R3.2.4). */
  maxConsecutiveFailures: number | null;
  /** The maximum losses, null for none, and how the openings they suspend resume (R3.2.2). */
  maxDailyLossPercent: string | null;
  maxDrawdownPercent: string | null;
  openingsResume: FakeOpeningsResume;
  memory: FakeMemory;
  trailingStop: FakeTrailingStop;
  consecutiveLossLimit: FakeConsecutiveLossLimit;
  /** The agent sees the exposure of the other flows of the account (R5.5.5). */
  accountExposureForAgent: boolean;
  /** The blocks of the reopenings in force now, as the API reads them from the closings (R5.5.2). */
  reopeningBlocks: FakeReopeningBlock[];
  /** What the agent would receive of the memory if the cycle started now, for every asset (R5.3.4). */
  remembered: FakeAssetMemory[];
  /** The suspension of the openings in force, null when the flow may open (R3.2.2). */
  openingsSuspension: FakeOpeningsSuspension | null;
  /** How many cycles the worker ran for the flow since the scenario started it (R2.4.1). */
  cycles: number;
  /** Why the flow paused, as the API says it (R1.2.4). */
  pauseReason: string | null;
  /** What the flow is worth now, as the API measures it (R2.2.2). */
  currentCapital: number;
  readonly history: FakeFlowHistory;
  /** The equity every cycle of the flow recorded, in the order the scenario records it. */
  readonly equity: FakeEquityPoint[];
  /** The price forecasts the flow recorded, whose error the API measures (R3.6.1). */
  readonly forecasts: FakeForecast[];
  readonly versions: FakeVersion[];
};

/**
 * An account of the fake platform; its public credential fields are kept in clear, empty for an account registered
 * before they were kept (Bug 401).
 */
export type FakeAccount = {
  readonly id: string;
  readonly name: string;
  /** What the account holds; an account of the simulated exchange holds its virtual balance (R6.3.2). */
  balance: number;
  publicFields: Record<string, string>;
  /** The exchange of the account: the one the fake platform supports unless it is the simulated one (R6.3.2). */
  exchange?: string;
  /** The currency the account settles in, which the results of its flows are written in (R6.4.2). */
  currency: string;
  /** The expiry of its credentials, read by the exchange or entered; none when unknown (R6.2.2). */
  expiry?: FakeKeyExpiry;
  /** The exchange of the account does not read the expiry: the user gives it (R6.2.2). */
  expiryEditable?: boolean;
  /** The exposure of its flows on one side, in percent of the balance; none unless the user sets it (R5.5.5). */
  maxDirectionExposurePercent?: string | null;
};

/**
 * A row of the history of the capital of an account, as the API answers it (R3.4.2): a change of the capital of one of
 * its flows, or a deposit or a withdrawal of the account, which has no flow and no capital before and after.
 */
export type FakeCapitalChange = {
  readonly accountId: string;
  readonly changed_at: string;
  readonly flow_id: string | null;
  readonly flow: string | null;
  readonly reason: string;
  readonly amount: string;
  readonly previous: string | null;
  readonly new: string | null;
};

/** What a scenario or a test changes of a flow: its status, why it paused and its capital. */
export type FakeFlowChanges = Partial<Omit<FakeFlow, 'id' | 'name'>>;

/** The configuration version in force of a flow, as the API answers it. */
export type FakeFlowConfiguration = {
  account_id: string | null;
  version: number;
  assets: string[];
  cycle_minutes: number;
  model: { name: string; parameters: Record<string, string> };
  sources: {
    name: string;
    adapters: {
      name: string;
      weight: number;
      parameters: Readonly<Record<string, FakeParameterValue>>;
    }[];
  }[];
  instructions: string;
  risk_limits: {
    max_leverage: number;
    max_margin_exposure_percent: string | null;
    max_value_exposure_percent: string | null;
    max_total_margin_exposure_percent: string | null;
    max_total_value_exposure_percent: string | null;
  };
  default_stop_loss_percent: string;
  default_take_profit_percent: string | null;
  minimum_confidence: number | null;
  allocated_capital: string | null;
  bring_to_minimum: boolean;
  system_prompt: string;
  system_prompt_is_default: boolean;
  system_prompt_placeholders: { name: string; description: string }[];
  max_consecutive_failures: number | null;
  max_daily_loss_percent: string | null;
  max_drawdown_percent: string | null;
  openings_resume: FakeOpeningsResume;
  memory: FakeMemory;
  trailing_stop: FakeTrailingStop;
  consecutive_loss_limit: FakeConsecutiveLossLimit;
  account_exposure_for_agent: boolean;
};

/** The configuration of the flow in force, in the shape of the answers of the API. */
export const configurationOf = (flow: FakeFlow): FakeFlowConfiguration => ({
  account_id: flow.accountId,
  version: flow.version,
  assets: flow.assets,
  cycle_minutes: flow.cycleMinutes,
  model: { name: flow.model, parameters: flow.modelParameters },
  sources: flow.sources.map((source) => ({
    name: source.name,
    adapters: source.adapters.map((adapter) => ({ parameters: {}, ...adapter })),
  })),
  instructions: flow.instructions,
  risk_limits: {
    max_leverage: flow.riskLimits.maxLeverage,
    max_margin_exposure_percent: flow.riskLimits.maxMarginExposurePercent,
    max_value_exposure_percent: flow.riskLimits.maxValueExposurePercent,
    max_total_margin_exposure_percent: flow.riskLimits.maxTotalMarginExposurePercent,
    max_total_value_exposure_percent: flow.riskLimits.maxTotalValueExposurePercent,
  },
  default_stop_loss_percent: flow.defaultStopLossPercent,
  default_take_profit_percent: flow.defaultTakeProfitPercent,
  minimum_confidence: flow.minimumConfidence,
  allocated_capital: flow.allocatedCapital === null ? null : String(flow.allocatedCapital),
  bring_to_minimum: flow.bringToMinimum,
  system_prompt: flow.systemPrompt ?? FAKE_SYSTEM_PROMPT.system_prompt,
  system_prompt_is_default: flow.systemPrompt === null,
  system_prompt_placeholders: FAKE_SYSTEM_PROMPT.system_prompt_placeholders,
  max_consecutive_failures: flow.maxConsecutiveFailures,
  max_daily_loss_percent: flow.maxDailyLossPercent,
  max_drawdown_percent: flow.maxDrawdownPercent,
  openings_resume: flow.openingsResume,
  memory: { ...flow.memory },
  trailing_stop: { ...flow.trailingStop },
  consecutive_loss_limit: flow.consecutiveLossLimit,
  account_exposure_for_agent: flow.accountExposureForAgent,
});

export const emptyHistory = (): FakeFlowHistory => ({ closedPositions: [], modelCalls: [] });

/** An email the mail server of a user delivered (R3.5.2, R3.5.5): the host it left from, too. */
export type FakeEmail = { readonly to: string; readonly subject: string; readonly host: string };

/** The mail server of a user, as the platform keeps it: the password stays on the platform (R3.5.5). */
export type FakeMailServer = {
  readonly host: string;
  readonly port: number;
  readonly security: 'STARTTLS' | 'TLS';
  readonly username: string;
  readonly sender: string;
  readonly password: string;
};

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
export type FakeProviderKey = {
  readonly provider: string;
  registeredAt: string;
  /** The expiry the user entered for the key; none when unknown (R6.2.2). */
  expiry?: FakeKeyExpiry;
};

export const FAKE_EXCHANGE = 'Hyperliquid';

/** The currency an account settles in unless a test says otherwise. */
export const SETTLEMENT_CURRENCY = 'USDC';
// The account address every fake account is registered with, a public field of the exchange (Bug 401).
export const FAKE_ACCOUNT_ADDRESS = '0xb2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2';
const registeredPublicFields = (): Record<string, string> => ({
  account_address: FAKE_ACCOUNT_ADDRESS,
});
/** The exchanges the fake platform supports, as the API lists them (ADR 0152). */
export const FAKE_SUPPORTED_EXCHANGES: readonly string[] = [FAKE_EXCHANGE];
/** The exchange that executes on the real market with a virtual balance, without credentials (R6.3.2). */
export const SIMULATED_EXCHANGE = 'simulato';

/** The networks the API names: the one the exchange is configured on, never deduced (Bug 277). */
export type FakeNetwork = 'test' | 'real';
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

/** The strategy file of a flow, as the API writes it: no account, capital, assets or keys (R2.5.2, ADR 0140). */
export type FakeStrategyDocument = {
  readonly format: string;
  readonly format_version: number;
  readonly strategy: {
    readonly cycle_minutes?: number;
    readonly model?: { readonly name: string; readonly parameters: Record<string, string> };
    readonly sources?: {
      readonly name: string;
      readonly adapters: { readonly name: string; readonly weight: number }[];
    }[];
    readonly instructions?: string;
    readonly risk_limits?: Record<string, number | string | null>;
    readonly bring_to_minimum?: boolean;
  };
};

export const STRATEGY_FORMAT = 'autotrading-strategy';
// The sources with their adapters came with the second version of the file (R4.1.1).
const STRATEGY_FORMAT_VERSION = 2;

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

/** The flow after a cash-out of its profits and what the cash-out freed (R3.4.1). */
export type FakeCashOut = {
  readonly flow: FakeFlow;
  readonly freed: number;
};

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
  maxTotalMarginExposurePercent: null,
  maxTotalValueExposurePercent: null,
};
const DRAFT = 'bozza';
const STOPPED = 'fermo';
const ACTIVE = 'attivo';
const SECOND = 1000;
// The reasons the API gives when it refuses a cycle asked for now (R6.5.2).
const FLOW_NOT_ACTIVE = 'il flusso non è attivo';
const CYCLE_IN_PROGRESS = 'un ciclo del flusso è già in corso';
const ARCHIVED = 'archiviato';
const PAUSED = 'in pausa';

// The transitions of the domain of the API, with the reasons it gives (R1.1.4-R1.1.6).
const TRANSITIONS: Record<FakeFlowCommand, Transition> = {
  pause: { from: [ACTIVE], to: PAUSED, refusal: refusedFor('pausa') },
  resume: { from: [PAUSED], to: ACTIVE, refusal: refusedFor('riprendi') },
  stop: { from: [ACTIVE, PAUSED], to: STOPPED, refusal: refusedFor('ferma') },
  archive: {
    from: [STOPPED, DRAFT],
    to: ARCHIVED,
    refusal: () => 'si archivia solo un flusso fermo',
  },
};

// Every flow, new or existing, has a stop loss default; 5% when nobody gave one (R3.1.2).
const DEFAULT_STOP_LOSS_PERCENT = '5';

export const FIRST_CONFIGURATION: FakeConfiguration = {
  assets: ['BTC'],
  cycleMinutes: 15,
  model: 'openai/gpt-4o',
  instructions: '',
  maxLeverage: 3,
  allocatedCapital: '100',
  systemPrompt: null,
  maxConsecutiveFailures: null,
  maxDailyLossPercent: null,
  maxDrawdownPercent: null,
  openingsResume: 'manual',
  defaultStopLossPercent: DEFAULT_STOP_LOSS_PERCENT,
  defaultTakeProfitPercent: null,
  minimumConfidence: null,
  memory: DEFAULT_MEMORY,
  trailingStop: DEFAULT_TRAILING_STOP,
  consecutiveLossLimit: null,
  accountExposureForAgent: false,
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
  notificationEmails: new Map<string, string>(),
  sentEmails: [] as FakeEmail[],
  mailServers: new Map<string, FakeMailServer>(),
  mailLoginRefused: false,
  linkCodes: new Map<string, FakeLinkCode>(),
  cycles: new Map<string, FakeCycle[]>(),
  cyclesInProgress: new Set<string>(),
  workerClock: undefined as Date | undefined,
  openPositions: new Map<string, FakeOpenPosition[]>(),
  closedPositions: new Map<string, ClosedPositionAnswer[]>(),
  cashOuts: [] as string[],
  emergencyClosings: [] as FakeEmergencyScope[],
  capitalChanges: [] as FakeCapitalChange[],
  signingIn: undefined as string | undefined,
  identityProviderSession: undefined as string | undefined,
  credentialPagesShown: 0,
  refreshTokensExpired: false,
  exchangeReachable: true,
  exchangesListed: true,
  exchangeNetwork: 'test' as FakeNetwork,
  exchangeNetworkName: 'testnet',
  exchangeReadsExpiry: true,
  simulatedExchangeOffered: false,
  apiAnswers: true,
};

export const flowIdOf = (name: string): string => `flow-${name}`;

/** What an emergency closing covers: one flow, the flows of one account, or every flow (R3.2.3). */
export type FakeEmergencyScope = { readonly flowId?: string; readonly accountId?: string };

/** What the emergency closing did to one flow, as the API answers it (R3.2.3). */
export type FakeEmergencyOutcome = {
  readonly flow: FakeFlow;
  readonly closed: string[];
};

export const EMERGENCY_REASON = 'chiusura di emergenza';

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
  const account = {
    id: `account-${name}`,
    name,
    balance: 1000,
    publicFields: registeredPublicFields(),
    currency: SETTLEMENT_CURRENCY,
  };
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
  sources: strategy.sources.map(copyOf),
  cycleMinutes: strategy.cycleMinutes,
  instructions: strategy.instructions ?? '',
  riskLimits: strategy.riskLimits ?? DEFAULT_RISK_LIMITS,
  defaultStopLossPercent: DEFAULT_STOP_LOSS_PERCENT,
  defaultTakeProfitPercent: null,
  minimumConfidence: null,
  bringToMinimum: strategy.bringToMinimum ?? false,
  systemPrompt: null,
  maxConsecutiveFailures: null,
  maxDailyLossPercent: null,
  maxDrawdownPercent: null,
  openingsResume: 'manual',
  memory: DEFAULT_MEMORY,
  trailingStop: DEFAULT_TRAILING_STOP,
  consecutiveLossLimit: null,
  accountExposureForAgent: false,
  reopeningBlocks: [],
  remembered: [],
  openingsSuspension: null,
  cycles: 0,
  pauseReason: null,
  currentCapital: 0,
  history: emptyHistory(),
  equity: [],
  forecasts: [],
  versions: versionsWith({}),
});

const modelOfStrategy = (document: FakeStrategyDocument): string => {
  if (document.format !== STRATEGY_FORMAT || document.format_version !== STRATEGY_FORMAT_VERSION) {
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

/** What the start of the flow waits for, as the API declares it: only a draft lacks its assignment (Bug 560). */
export const missingBeforeStartOf = (flow: FakeFlow): string[] =>
  flow.status === DRAFT ? missingOf(flow) : [];

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
    fakeClock.release();
    state.users.clear();
    state.chats.clear();
    state.linkedChats.clear();
    state.notificationEmails.clear();
    state.sentEmails = [];
    state.mailServers.clear();
    state.mailLoginRefused = false;
    state.linkCodes.clear();
    state.cycles.clear();
    state.cyclesInProgress.clear();
    state.workerClock = undefined;
    state.openPositions.clear();
    state.closedPositions.clear();
    state.cashOuts.length = 0;
    state.emergencyClosings.length = 0;
    state.capitalChanges.length = 0;
    state.signingIn = undefined;
    state.identityProviderSession = undefined;
    state.credentialPagesShown = 0;
    state.refreshTokensExpired = false;
    state.exchangeReachable = true;
    state.exchangesListed = true;
    state.exchangeNetwork = 'test';
    state.exchangeNetworkName = 'testnet';
    state.exchangeReadsExpiry = true;
    state.simulatedExchangeOffered = false;
    state.apiAnswers = true;
    fakeReconciliation.reset();
    fakeNotificationChannels.reset();
    fakeAlerts.reset();
    fakeInbox.reset();
    fakeSourceCredentials.reset();
    fakeSourceTrials.reset();
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

  /**
   * The key of the user for the provider, saved at the instant: a new instant on every replacement, which keeps only the
   * expiry given with the new key (R6.2.2).
   */
  saveProviderKey(
    account: string,
    provider: string,
    registeredAt: string,
    expiry?: FakeKeyExpiry,
  ): FakeProviderKey {
    const user = userNamed(account);
    const saved = user.providerKeys.find((key) => key.provider === provider);
    if (saved !== undefined) {
      saved.registeredAt = registeredAt;
      saved.expiry = expiry;
      return saved;
    }
    const created = { provider, registeredAt, expiry };
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
      defaultStopLossPercent: DEFAULT_STOP_LOSS_PERCENT,
      defaultTakeProfitPercent: null,
      minimumConfidence: null,
      bringToMinimum: false,
      systemPrompt: null,
      maxConsecutiveFailures: null,
      maxDailyLossPercent: null,
      maxDrawdownPercent: null,
      openingsResume: 'manual',
      memory: DEFAULT_MEMORY,
      trailingStop: DEFAULT_TRAILING_STOP,
      consecutiveLossLimit: null,
      accountExposureForAgent: false,
      reopeningBlocks: [],
      remembered: [],
      openingsSuspension: null,
      cycles: 0,
      pauseReason: null,
      currentCapital: 100,
      history: emptyHistory(),
      equity: [],
      forecasts: [],
      versions: versionsWith({}),
      ...rest,
    };
    user.flows.push(flow);
    return flow;
  },

  /** The account was registered before its public fields were kept: a replacement asks them all (Bug 401). */
  forgetPublicFieldsOf(account: string, name: string): void {
    accountOf(userNamed(account), name).publicFields = {};
  },

  /** The account belongs to the user, who has the Utente role: the user is created when missing. */
  giveAccountTo(account: string, name: string, balance: number): FakeAccount {
    if (!state.users.has(account)) {
      this.addUser(account, { hasUserRole: true });
    }
    const created = {
      id: `account-${name}`,
      name,
      balance,
      publicFields: registeredPublicFields(),
      currency: SETTLEMENT_CURRENCY,
    };
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

  /** From now on the API fails listing the exchanges it supports, with its generic reason (R2.3.8). */
  stopListingExchanges(): void {
    state.exchangesListed = false;
  },

  listsExchanges(): boolean {
    return state.exchangesListed;
  },

  /** From now on the exchange is configured on this network, as the installation declares it (Bug 277). */
  configureExchangeNetwork(network: FakeNetwork, name?: string): void {
    state.exchangeNetwork = network;
    state.exchangeNetworkName = name ?? (network === 'real' ? 'mainnet' : 'testnet');
  },

  exchangeNetwork(): FakeNetwork {
    return state.exchangeNetwork;
  },

  /** The name the adapter of the exchange gives its network (R2.3.10). */
  exchangeNetworkName(): string {
    return state.exchangeNetworkName;
  },

  /** Whether the exchange reads the expiry of the credentials, as Hyperliquid does; the user gives it otherwise (R6.2.2). */
  exchangeReadsExpiry(): boolean {
    return state.exchangeReadsExpiry;
  },

  /** From now on the exchange does not read the expiry of the credentials: the user gives it (R6.2.2). */
  stopReadingExpiry(): void {
    state.exchangeReadsExpiry = false;
  },

  /** From now on the platform offers the simulated exchange too, as an installation that composes it (R6.3.2). */
  offerSimulatedExchange(): void {
    state.simulatedExchangeOffered = true;
  },

  offersSimulatedExchange(): boolean {
    return state.simulatedExchangeOffered;
  },

  /** An account of the user on the simulated exchange, with the virtual balance given and no credentials (R6.3.2). */
  addSimulatedAccount(account: string, name: string, balance: number): FakeAccount {
    state.simulatedExchangeOffered = true;
    const added = accountOf(userNamed(account), name);
    added.exchange = SIMULATED_EXCHANGE;
    added.balance = balance;
    added.publicFields = {};
    return added;
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
              maxTotalMarginExposurePercent: limits.max_total_margin_exposure_percent,
              maxTotalValueExposurePercent: limits.max_total_value_exposure_percent,
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

  /** The account has the Utente role: it is created when missing, kept as it is otherwise. */
  ensureUser(account: string): void {
    if (!state.users.has(account)) {
      this.addUser(account, { hasUserRole: true });
    }
  },

  /** The flow belongs to the account, which has the Utente role: both are created when missing. */
  giveFlowTo(account: string, name: string): FakeFlow {
    this.ensureUser(account);
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

  /** A cycle of the flow concludes: from now on the API lists it (R2.1.2). */
  concludeCycle(flowName: string, plannedAt: Date): void {
    const flowId = flowIdOf(flowName);
    state.cycles.set(flowId, [...(state.cycles.get(flowId) ?? []), aCompletedCycle(plannedAt)]);
  },

  /** From now on the worker reads this instant as now: a cycle asked for now is planned at it (R6.5.2). */
  setWorkerClock(instant: Date): void {
    state.workerClock = instant;
  },

  /** A cycle of the flow is under way: a cycle asked for now is refused until it ends (R6.5.2). */
  holdCycle(flowName: string): void {
    state.cyclesInProgress.add(flowIdOf(flowName));
  },

  /**
   * The worker runs a full cycle of the active flow now, planned at the instant of the request, and records it as asked
   * for (R6.5.2); a flow not active or with a cycle under way refuses it, as the API does.
   */
  runCycleNow(user: FakeUser, flowId: string): FakeCycle {
    const flow = flowOf(user, flowId);
    if (flow.status !== ACTIVE) {
      throw new FakeRefusal(409, FLOW_NOT_ACTIVE);
    }
    if (state.cyclesInProgress.has(flow.id)) {
      throw new FakeRefusal(409, CYCLE_IN_PROGRESS);
    }
    const now = state.workerClock ?? new Date(Math.floor(Date.now() / SECOND) * SECOND);
    const cycle: FakeCycle = { ...aCompletedCycle(now), trigger: 'on_demand' };
    state.cycles.set(flow.id, [...(state.cycles.get(flow.id) ?? []), cycle]);
    return cycle;
  },

  /** From now on the API does not answer: every request fails on the network (R2.1.2). */
  stopApi(): void {
    state.apiAnswers = false;
  },

  apiAnswers(): boolean {
    return state.apiAnswers;
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

  /** The address the notifications of the user go to by email, if any (R3.5.2). */
  notificationEmailOf(account: string): string | undefined {
    return state.notificationEmails.get(account);
  },

  setNotificationEmail(account: string, address: string): void {
    state.notificationEmails.set(account, address);
  },

  removeNotificationEmail(account: string): void {
    state.notificationEmails.delete(account);
  },

  /** The mail server of the user, if any: without one the address is kept, but no email leaves (R3.5.5). */
  mailServerOf(account: string): FakeMailServer | undefined {
    return state.mailServers.get(account);
  },

  saveMailServer(account: string, server: FakeMailServer): void {
    state.mailServers.set(account, server);
  },

  removeMailServer(account: string): void {
    state.mailServers.delete(account);
  },

  /** Whether the mail servers refuse the login of the user, as for a wrong password. */
  mailLoginRefused(): boolean {
    return state.mailLoginRefused;
  },

  refuseMailLogin(): void {
    state.mailLoginRefused = true;
  },

  sendEmail(email: FakeEmail): void {
    state.sentEmails.push(email);
  },

  emailsTo(address: string): FakeEmail[] {
    return state.sentEmails.filter((email) => email.to === address);
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

  /** The account the flow with the name trades on (R6.4.2). */
  accountOfFlow(name: string): FakeAccount {
    const { accountId } = fakePlatform.flowNamed(name);
    const account = [...state.users.values()]
      .flatMap((user) => user.accounts)
      .find((candidate) => candidate.id === accountId);
    if (account === undefined) {
      throw new Error(`fake flow ${name} has no account`);
    }
    return account;
  },

  duplicate(user: FakeUser, flowId: string): FakeFlow {
    const original = flowOf(user, flowId);
    const name = `${original.name} (copia)`;
    requireFreeName(user, name);
    // The copy keeps account and capital of the original, not its assets: two flows of one account never share
    // one (RF-02.05, ADR bozza-configurata-dall-editor-e-duplica-con-conto).
    const copy = {
      ...draftOf(name, original),
      accountId: original.accountId,
      allocatedCapital: original.allocatedCapital,
    };
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
      format_version: STRATEGY_FORMAT_VERSION,
      strategy: {
        cycle_minutes: flow.cycleMinutes,
        model: { name: flow.model, parameters: {} },
        sources: flow.sources.map((source) => ({
          name: source.name,
          adapters: source.adapters.map((adapter) => ({ ...adapter, parameters: {} })),
        })),
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
      sources: (document.strategy.sources ?? []).map(({ name, adapters }) => ({
        name,
        adapters: adapters.map((adapter) => ({ name: adapter.name, weight: adapter.weight })),
      })),
      cycleMinutes: document.strategy.cycle_minutes ?? 15,
    });
    user.flows.push(draft);
    return draft;
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
    // The pause of the flow is over: its alert resolves on its own (R6.2.3).
    if (command !== 'pause') {
      fakeAlerts.resolveFlowPause(flow.id, new Date());
    }
    return flow;
  },

  /**
   * The cash-out of the profits of the flow, refused as the API refuses it: it closes every position, keeps the capital
   * asked for, or the capital allocated now, and frees the rest of what the flow is worth (R3.4.1).
   */
  cashOut(user: FakeUser, flowId: string, capital: number | undefined): FakeCashOut {
    const flow = flowOf(user, flowId);
    const allocated = flow.allocatedCapital ?? 0;
    if (flow.currentCapital <= allocated) {
      throw new FakeRefusal(409, `${flow.name} non ha profitti da incassare`);
    }
    const kept = capital ?? allocated;
    if (kept <= 0 || kept >= flow.currentCapital) {
      throw new FakeRefusal(
        400,
        `il capitale indicato è maggiore di 0 e minore del valore del flusso, ${String(flow.currentCapital)} USDC`,
      );
    }
    state.openPositions.delete(flow.id);
    const freed = flow.currentCapital - kept;
    flow.allocatedCapital = kept;
    flow.currentCapital = kept;
    state.cashOuts.push(flow.id);
    return { flow, freed };
  },

  /**
   * The flows an emergency closing covers, refused as the API refuses a flow or an account the user lacks: active or
   * paused, of the flow, of the account or of every account (R3.2.3).
   */
  emergencyFlowsOf(user: FakeUser, scope: FakeEmergencyScope): FakeFlow[] {
    if (scope.flowId !== undefined && scope.accountId !== undefined) {
      throw new FakeRefusal(400, 'indicare un flusso o un conto, non entrambi');
    }
    if (scope.flowId !== undefined) {
      flowOf(user, scope.flowId);
    }
    if (
      scope.accountId !== undefined &&
      !user.accounts.some((each) => each.id === scope.accountId)
    ) {
      throw new FakeRefusal(404, 'conto non trovato');
    }
    return user.flows.filter(
      (flow) =>
        (flow.status === ACTIVE || flow.status === PAUSED) &&
        (scope.flowId === undefined || flow.id === scope.flowId) &&
        (scope.accountId === undefined || flow.accountId === scope.accountId),
    );
  },

  /** The emergency closing: every position of the flows of the scope closes, the active flows pause (R3.2.3). */
  closeInEmergency(user: FakeUser, scope: FakeEmergencyScope): FakeEmergencyOutcome[] {
    const outcomes = fakePlatform.emergencyFlowsOf(user, scope).map((flow) => {
      const closed = fakePlatform.openPositionsOf(flow.id).map((position) => position.asset);
      state.openPositions.delete(flow.id);
      if (flow.status === ACTIVE) {
        flow.status = PAUSED;
        flow.pauseReason = EMERGENCY_REASON;
      }
      return { flow, closed };
    });
    state.emergencyClosings.push(scope);
    return outcomes;
  },

  /** How many emergency closings the fake API ran. */
  emergencyClosings(): number {
    return state.emergencyClosings.length;
  },

  /** A row of the history of the capital, in any order: the fake API serves them from the most recent (R3.4.2). */
  recordCapitalChange(change: FakeCapitalChange): void {
    state.capitalChanges.push(change);
  },

  capitalChangesOfAccount(accountId: string): FakeCapitalChange[] {
    return state.capitalChanges.filter((change) => change.accountId === accountId);
  },

  /** How many cash-outs of the flow with the name the fake API ran. */
  cashOutsOf(flowName: string): number {
    return state.cashOuts.filter((flowId) => flowId === flowIdOf(flowName)).length;
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

  /** The account the user types on the page of the credentials of the identity provider, used by the next sending. */
  signIn(account: string): void {
    state.signingIn = account;
  },

  /** The account the user typed, once: a page of the credentials asked again waits for the user again. */
  takeSigningInAccount(): string | undefined {
    const account = state.signingIn;
    state.signingIn = undefined;
    return account;
  },

  /** The account whose session the identity provider keeps after a sign-in, until it ends. */
  startIdentityProviderSession(account: string): void {
    state.identityProviderSession = account;
  },

  identityProviderSession(): string | undefined {
    return state.identityProviderSession;
  },

  /** The session at the identity provider is over: the next sign-in asks the credentials (R6.5.1). */
  endIdentityProviderSession(): void {
    state.identityProviderSession = undefined;
  },

  countCredentialPage(): void {
    state.credentialPagesShown += 1;
  },

  /** How many times the identity provider asked the credentials. */
  credentialPagesShown(): number {
    return state.credentialPagesShown;
  },

  /** From now on the identity provider refuses to renew the tokens it issued, while its session lives on (R6.5.1). */
  expireRefreshTokens(): void {
    state.refreshTokensExpired = true;
  },

  refreshTokensExpired(): boolean {
    return state.refreshTokensExpired;
  },

  /** The access expired: the identity provider renews no token and its session is over, the user signs in again. */
  expireSessions(): void {
    state.refreshTokensExpired = true;
    state.identityProviderSession = undefined;
  },

  restoreSessions(): void {
    state.refreshTokensExpired = false;
  },

  sessionsExpired(): boolean {
    return state.refreshTokensExpired && state.identityProviderSession === undefined;
  },
};
