import { FAKE_MODELS, FAKE_SYSTEM_PROMPT, type FakeSource as FakeCatalogSource } from './catalogs';
import {
  fakePlatform,
  DEFAULT_MEMORY,
  DEFAULT_TRAILING_STOP,
  type FakeAccount,
  type FakeAdapterChoice,
  type FakeConsecutiveLossLimit,
  type FakeFlow,
  type FakeMemory,
  type FakeOpeningsResume,
  type FakeRiskLimits,
  type FakeSource,
  type FakeTrailingStop,
  type FakeUser,
} from './platform';
import { fakeSourceCredentials, notConfiguredReason } from './source-credentials';
import { listOutcomeOf, type FakeParameterValue } from './source-parameters';

/**
 * A configuration the API refuses, with the status, the reason and the setting it names, as the API answers it
 * (R1.1.1-R1.1.3, R1.1.7, R2.3.3). Only the rules the tests of the dashboard go through are here.
 */
export class Refusal extends Error {
  readonly status: number;
  readonly field: string | undefined;

  constructor(status: number, reason: string, field?: string) {
    super(reason);
    this.status = status;
    this.field = field;
  }
}

/** A request the API refuses before reading it, with where and why, as its validation answers. */
export class InvalidRequest extends Error {
  readonly field: string;

  constructor(field: string, reason: string) {
    super(reason);
    this.field = field;
  }
}

type AdapterRequest = { name?: unknown; weight?: unknown; parameters?: unknown };

type SourceRequest = { name?: unknown; adapters?: unknown };

type ConfigurationRequest = {
  name?: unknown;
  account_id?: unknown;
  assets?: unknown;
  cycle_minutes?: unknown;
  model?: unknown;
  model_parameters?: unknown;
  sources?: unknown;
  instructions?: unknown;
  max_leverage?: unknown;
  max_margin_exposure_percent?: unknown;
  max_value_exposure_percent?: unknown;
  max_total_margin_exposure_percent?: unknown;
  max_total_value_exposure_percent?: unknown;
  default_stop_loss_percent?: unknown;
  default_take_profit_percent?: unknown;
  minimum_confidence?: unknown;
  allocated_capital?: unknown;
  bring_to_minimum?: unknown;
  system_prompt?: unknown;
  max_consecutive_failures?: unknown;
  max_daily_loss_percent?: unknown;
  max_drawdown_percent?: unknown;
  openings_resume?: unknown;
  memory?: {
    active?: unknown;
    decisions?: unknown;
    days?: unknown;
    text_length?: unknown;
    all_decisions?: unknown;
    summary?: unknown;
    other_assets?: unknown;
    unlimited_text_length?: unknown;
  };
  trailing_stop?: {
    distance_percent?: unknown;
    activation_percent?: unknown;
    breakeven_percent?: unknown;
    max_profit_in_context?: unknown;
    remove_distance?: unknown;
    remove_activation?: unknown;
    remove_breakeven?: unknown;
  };
  consecutive_loss_limit?: {
    max_consecutive_losses?: unknown;
    loss_window_hours?: unknown;
    block_minutes?: unknown;
    count_scope?: unknown;
    remove_limit?: unknown;
  };
  account_exposure_for_agent?: unknown;
  fees_for_agent?: unknown;
};

const DEFAULT_CYCLE_MINUTES = 15;
const MAX_CYCLE_MINUTES = 1440;
const DEFAULT_WEIGHT = 5;
const MAX_WEIGHT = 10;
const STOPPED = 'fermo';
const CURRENCY = 'USDC';

const moneyText = (amount: number, currency: string): string => {
  const text = Number.isInteger(amount) ? String(amount) : amount.toFixed(2).replace('.', ',');
  return `${text} ${currency}`;
};

const textOf = (value: unknown): string => (typeof value === 'string' ? value : '');

const numberOf = (value: unknown, field: string): number => {
  const number = typeof value === 'number' ? value : Number(value);
  if (value === null || value === '' || Number.isNaN(number)) {
    throw new InvalidRequest(field, 'Input should be a valid number');
  }
  return number;
};

const optionalTextOf = (value: unknown): string | null =>
  value === undefined || value === null ? null : String(value);

const PLACEHOLDER = /\{(\w+)\}/g;
const KNOWN_PLACEHOLDERS = new Set(
  FAKE_SYSTEM_PROMPT.system_prompt_placeholders.map(({ name }) => name),
);

// An unknown placeholder refused, with the reason of the API; null follows the default (R1.4.8).
const systemPromptOf = (value: unknown): string | null => {
  const text = optionalTextOf(value);
  const unknown = [...(text ?? '').matchAll(PLACEHOLDER)]
    .map(([, name]) => name)
    .find((name) => name !== undefined && !KNOWN_PLACEHOLDERS.has(name));
  if (unknown !== undefined) {
    throw new Refusal(422, `il segnaposto "${unknown}" non esiste`, 'system_prompt');
  }
  return text;
};

// The range of the minimum confidence, as the API checks it (R3.1.4).
const minimumConfidenceOf = (requested: unknown): number | null => {
  if (requested === undefined || requested === null) {
    return null;
  }
  const minimum = numberOf(requested, 'minimum_confidence');
  if (minimum < 0 || minimum > 100) {
    throw new Refusal(422, 'la confidenza minima va da 0 a 100', 'minimum_confidence');
  }
  return minimum;
};

// A whole motive takes the length away; a length not sent keeps the one in force; zero or less is refused (R5.3.5).
const textLengthOf = (
  requested: ConfigurationRequest['memory'],
  current: number | null,
): number | null => {
  if (requested?.unlimited_text_length === true) {
    return null;
  }
  const sent = requested?.text_length;
  if (sent === undefined || sent === null) {
    return current;
  }
  const length = numberOf(sent, 'memory.text_length');
  if (length < 1) {
    throw new Refusal(
      422,
      'la lunghezza del motivo della memoria è un intero positivo',
      'memory.text_length',
    );
  }
  return length;
};

// The memory with the parts sent, the others kept, within the ranges the API checks (R5.3.4).
const memoryOf = (requested: ConfigurationRequest['memory'], current: FakeMemory): FakeMemory => {
  const part = (value: unknown, field: string, kept: number): number =>
    value === undefined || value === null ? kept : numberOf(value, field);
  const decisions = part(requested?.decisions, 'memory.decisions', current.decisions);
  if (decisions < 1 || decisions > 50) {
    throw new Refusal(422, 'le decisioni della memoria vanno da 1 a 50', 'memory.decisions');
  }
  const days = part(requested?.days, 'memory.days', current.days);
  if (days < 1 || days > 365) {
    throw new Refusal(422, 'i giorni della memoria vanno da 1 a 365', 'memory.days');
  }
  const switched = (sent: unknown, kept: boolean): boolean =>
    typeof sent === 'boolean' ? sent : kept;
  return {
    active: switched(requested?.active, current.active),
    decisions,
    days,
    text_length: textLengthOf(requested, current.text_length),
    all_decisions: switched(requested?.all_decisions, current.all_decisions),
    summary: switched(requested?.summary, current.summary),
    other_assets: switched(requested?.other_assets, current.other_assets),
  };
};

// A part sent changes, a remove flag takes it away, a part not sent keeps the value in force (R5.5.1).
const trailingPartOf = (sent: unknown, removed: unknown, kept: string | null): string | null => {
  if (removed === true) {
    return null;
  }
  return sent === undefined || sent === null ? kept : String(sent);
};

// The stop that follows the price with the rules the API checks, the reasons as it gives them (R5.5.1).
const trailingStopOf = (
  requested: ConfigurationRequest['trailing_stop'],
  current: FakeTrailingStop,
): FakeTrailingStop => {
  const trailing = {
    distance_percent: trailingPartOf(
      requested?.distance_percent,
      requested?.remove_distance,
      current.distance_percent,
    ),
    activation_percent: trailingPartOf(
      requested?.activation_percent,
      requested?.remove_activation,
      current.activation_percent,
    ),
    breakeven_percent: trailingPartOf(
      requested?.breakeven_percent,
      requested?.remove_breakeven,
      current.breakeven_percent,
    ),
    max_profit_in_context:
      typeof requested?.max_profit_in_context === 'boolean'
        ? requested.max_profit_in_context
        : current.max_profit_in_context,
  };
  const distance = trailing.distance_percent === null ? null : Number(trailing.distance_percent);
  if (distance !== null && (distance < 0.1 || distance > 50)) {
    throw new Refusal(
      422,
      'la distanza dello stop che segue va da 0,1 a 50',
      'trailing_stop.distance_percent',
    );
  }
  if (trailing.activation_percent !== null && distance === null) {
    throw new Refusal(
      422,
      "l'attivazione richiede la distanza dello stop che segue",
      'trailing_stop.activation_percent',
    );
  }
  return trailing;
};

const LOSS_LIMIT_PARTS = [
  ['max_consecutive_losses', 'le perdite consecutive massime sono almeno 1'],
  ['loss_window_hours', 'la finestra delle perdite è di almeno 1 ora'],
  ['block_minutes', 'la durata del blocco è di almeno 1 minuto'],
] as const;

const givenOf = (value: unknown): boolean => value !== undefined && value !== null;

// The block of the reopenings with the rules the API checks, the reasons as it gives them (R5.5.2): nothing sent keeps
// the limit in force, the flag takes it away, any part sent replaces it whole.
const consecutiveLossLimitOf = (
  requested: ConfigurationRequest['consecutive_loss_limit'],
  current: FakeConsecutiveLossLimit,
): FakeConsecutiveLossLimit => {
  if (requested?.remove_limit === true) {
    return null;
  }
  const numbers = LOSS_LIMIT_PARTS.map(([part]) => requested?.[part]);
  if (!numbers.some(givenOf) && !givenOf(requested?.count_scope)) {
    return current;
  }
  if (!numbers.every(givenOf)) {
    throw new Refusal(
      422,
      'perdite consecutive massime, finestra delle perdite e durata del blocco si impostano insieme',
      'consecutive_loss_limit.max_consecutive_losses',
    );
  }
  LOSS_LIMIT_PARTS.forEach(([part, reason], index) => {
    if (Number(numbers[index]) < 1) {
      throw new Refusal(422, reason, `consecutive_loss_limit.${part}`);
    }
  });
  const scope = requested?.count_scope ?? 'asset';
  if (scope !== 'asset' && scope !== 'flusso') {
    throw new Refusal(
      422,
      "l'ambito del conteggio è asset oppure flusso",
      'consecutive_loss_limit.count_scope',
    );
  }
  return {
    max_consecutive_losses: Number(numbers[0]),
    loss_window_hours: Number(numbers[1]),
    block_minutes: Number(numbers[2]),
    count_scope: scope,
  };
};

const assetsOf = (requested: unknown): string[] => {
  const names = Array.isArray(requested) ? requested.map(textOf) : [];
  const assets = [
    ...new Set(names.map((name) => name.trim().toUpperCase()).filter((name) => name !== '')),
  ];
  if (assets.length === 0) {
    throw new Refusal(422, 'almeno un asset è obbligatorio', 'assets');
  }
  return assets;
};

const cycleMinutesOf = (requested: unknown): number => {
  const minutes =
    requested === undefined || requested === null
      ? DEFAULT_CYCLE_MINUTES
      : numberOf(requested, 'cycle_minutes');
  if (minutes < 1 || minutes > MAX_CYCLE_MINUTES) {
    throw new Refusal(422, 'intervallo di ciclo fuori da 1-1440 minuti', 'cycle_minutes');
  }
  return minutes;
};

const modelOf = (user: FakeUser, name: unknown, parameters: unknown) => {
  const requested = textOf(name).trim();
  if (requested === '') {
    throw new Refusal(422, 'modello obbligatorio', 'model');
  }
  const model = FAKE_MODELS.find((candidate) => candidate.name === requested);
  if (model === undefined) {
    throw new Refusal(422, `modello non disponibile: ${requested}`, 'model');
  }
  if (!user.providerKeys.some((key) => key.provider === model.provider)) {
    throw new Refusal(
      422,
      `nessuna chiave registrata per il fornitore: ${model.provider}`,
      'model',
    );
  }
  const given = (parameters ?? {}) as Record<string, unknown>;
  const resolved = Object.fromEntries(
    model.parameters.map((parameter) => [
      parameter.key,
      String(given[parameter.key] ?? parameter.default),
    ]),
  );
  return { name: model.name, parameters: resolved };
};

// Every adapter chosen, checked against what it declares in the catalog, as the API does (R4.1.1).
const adapterOf = (
  source: FakeCatalogSource,
  request: AdapterRequest,
  account: string,
): FakeAdapterChoice => {
  const name = textOf(request.name);
  const adapter = source.adapters.find((candidate) => candidate.name === name);
  if (adapter === undefined) {
    throw new Refusal(
      422,
      `adapter non disponibile per la fonte ${source.name}: ${name}`,
      'sources',
    );
  }
  // An adapter that needs credentials the tenant did not give is not activatable (R4.1.2).
  if (
    adapter.configuration_fields.length > 0 &&
    fakeSourceCredentials.of(account, name) === undefined
  ) {
    throw new Refusal(422, notConfiguredReason(name), 'sources');
  }
  const weight =
    request.weight === undefined || request.weight === null
      ? DEFAULT_WEIGHT
      : Number(request.weight);
  if (weight < 1 || weight > MAX_WEIGHT) {
    throw new Refusal(422, `peso fuori da 1-10: ${source.name}`, 'sources');
  }
  const given = (request.parameters ?? {}) as Record<string, unknown>;
  // Every list follows the common rules from its declaration alone (ADR parametri-delle-fonti-come-liste-libere).
  const lists: Record<string, readonly number[]> = {};
  for (const parameter of adapter.parameters) {
    if (parameter.kind === 'list' && given[parameter.key] !== undefined) {
      const outcome = listOutcomeOf(parameter, given[parameter.key]);
      if ('refusal' in outcome) {
        throw new Refusal(422, outcome.refusal, 'sources');
      }
      lists[parameter.key] = outcome.saved;
    }
  }
  const numbers = given as Record<string, number>;
  const notAmongChoices = adapter.parameters.find((parameter) => {
    const value = numbers[parameter.key];
    return (
      value !== undefined &&
      parameter.choices.length > 0 &&
      !parameter.choices.some((choice) => choice.value === value)
    );
  });
  if (notAmongChoices !== undefined) {
    const labels = notAmongChoices.choices.map((choice) => choice.label).join(', ');
    throw new Refusal(422, `${notAmongChoices.label}: ammessi ${labels}`, 'sources');
  }
  const outOfRange = adapter.parameters.find((parameter) => {
    const value = numbers[parameter.key];
    return (
      parameter.kind === 'number' &&
      value !== undefined &&
      (value < parameter.minimum || value > parameter.maximum)
    );
  });
  if (outOfRange !== undefined) {
    throw new Refusal(
      422,
      `parametro fuori dai valori ammessi: ${outOfRange.label}, da ${outOfRange.minimum} a ${outOfRange.maximum}`,
      'sources',
    );
  }
  const parameters = Object.fromEntries(
    adapter.parameters.map((parameter): [string, FakeParameterValue] => [
      parameter.key,
      lists[parameter.key] ?? numbers[parameter.key] ?? parameter.default,
    ]),
  );
  return { name, weight, parameters };
};

const sourceOf = (request: SourceRequest, account: string): FakeSource => {
  const name = textOf(request.name);
  const source = fakeSourceCredentials.sources().find((candidate) => candidate.name === name);
  if (source === undefined) {
    throw new Refusal(422, `fonte non disponibile: ${name}`, 'sources');
  }
  const requested = (Array.isArray(request.adapters) ? request.adapters : []) as AdapterRequest[];
  if (requested.length === 0) {
    throw new Refusal(422, `scegli almeno un adapter della fonte ${name}`, 'sources');
  }
  const adapters = requested.map((adapter) => adapterOf(source, adapter, account));
  const repeated = adapters.find(
    (adapter, index) => adapters.findIndex((other) => other.name === adapter.name) !== index,
  );
  if (repeated !== undefined) {
    throw new Refusal(422, `adapter ripetuto nella fonte ${name}: ${repeated.name}`, 'sources');
  }
  return { name, adapters };
};

const sourcesOf = (requested: unknown, account: string): FakeSource[] => {
  const sources = (Array.isArray(requested) ? requested : []) as SourceRequest[];
  const selected = sources.map((source) => sourceOf(source, account));
  const repeated = selected.find(
    (source, index) => selected.findIndex((other) => other.name === source.name) !== index,
  );
  if (repeated !== undefined) {
    throw new Refusal(422, `fonte ripetuta: ${repeated.name}`, 'sources');
  }
  return selected;
};

// The rule of the domain of the API, with its reason (R3.2.1).
const totalExposureOf = (value: unknown, field: string): string | null => {
  const text = optionalTextOf(value);
  const percent = Number(text);
  if (text !== null && !(percent >= 0.1 && percent <= 1000)) {
    throw new Refusal(422, "l'esposizione complessiva massima va da 0,1 a 1000", field);
  }
  return text;
};

type ExposureRequest = {
  readonly margin: unknown;
  readonly value: unknown;
  readonly totalMargin: unknown;
  readonly totalValue: unknown;
};

const riskLimitsOf = (maxLeverage: unknown, exposures: ExposureRequest): FakeRiskLimits => {
  if (maxLeverage === undefined || maxLeverage === null) {
    throw new Refusal(422, 'la leva massima è obbligatoria', 'max_leverage');
  }
  const limits = {
    maxLeverage: numberOf(maxLeverage, 'max_leverage'),
    maxMarginExposurePercent: optionalTextOf(exposures.margin),
    maxValueExposurePercent: optionalTextOf(exposures.value),
    maxTotalMarginExposurePercent: totalExposureOf(
      exposures.totalMargin,
      'max_total_margin_exposure_percent',
    ),
    maxTotalValueExposurePercent: totalExposureOf(
      exposures.totalValue,
      'max_total_value_exposure_percent',
    ),
  };
  if (limits.maxMarginExposurePercent === null && limits.maxValueExposurePercent === null) {
    throw new Refusal(
      422,
      'almeno un limite di esposizione è obbligatorio',
      'max_margin_exposure_percent',
    );
  }
  if (limits.maxLeverage < 1) {
    throw new Refusal(422, 'limite di rischio non valido: leva massima', 'max_leverage');
  }
  return limits;
};

const capitalOf = (requested: unknown): number => {
  if (requested === undefined) {
    throw new InvalidRequest('allocated_capital', 'Field required');
  }
  const capital = numberOf(requested, 'allocated_capital');
  if (capital <= 0) {
    throw new Refusal(422, 'il capitale allocato deve essere positivo', 'allocated_capital');
  }
  return capital;
};

const accountOf = (user: FakeUser, accountId: string): FakeAccount => {
  const account = user.accounts.find((candidate) => candidate.id === accountId);
  if (account === undefined) {
    throw new Refusal(404, 'conto non trovato');
  }
  return account;
};

// The flows that hold the account, neither draft nor archived, share neither assets nor capital (R1.1.1, R1.1.2).
const othersOnAccount = (user: FakeUser, accountId: string, excluding?: FakeFlow): FakeFlow[] =>
  user.flows.filter(
    (flow) =>
      flow !== excluding &&
      flow.accountId === accountId &&
      flow.status !== 'bozza' &&
      flow.status !== 'archiviato',
  );

const requireAssetsFree = (
  user: FakeUser,
  accountId: string,
  assets: string[],
  excluding?: FakeFlow,
): void => {
  for (const flow of othersOnAccount(user, accountId, excluding)) {
    const shared = assets.filter((asset) => flow.assets.includes(asset));
    if (shared.length > 0) {
      throw new Refusal(
        409,
        `asset già assegnati al flusso ${flow.name} sullo stesso conto: ${shared.join(', ')}`,
        'assets',
      );
    }
  }
};

const freeCapitalOf = (user: FakeUser, account: FakeAccount): number =>
  fakePlatform.freeCapitalOfAccount(user, account);

// The rule of the domain of the API, with its reason (R3.2.4).
const maxConsecutiveFailuresOf = (value: unknown): number | null => {
  if (value === null) {
    return null;
  }
  const maximum = Number(value);
  if (!Number.isInteger(maximum) || maximum < 1 || maximum > 100) {
    throw new Refusal(
      400,
      'il massimo di cicli falliti consecutivi va da 1 a 100',
      'max_consecutive_failures',
    );
  }
  return maximum;
};

// The rule of the domain of the API, with its reason (R3.2.2).
const maxLossOf = (value: unknown, field: string): string | null => {
  const text = optionalTextOf(value);
  const percent = Number(text);
  if (text !== null && !(percent >= 0.1 && percent <= 100)) {
    throw new Refusal(422, 'la perdita massima va da 0,1 a 100', field);
  }
  return text;
};

const openingsResumeOf = (value: unknown): FakeOpeningsResume =>
  value === 'next_day' ? 'next_day' : 'manual';

/** The flow as its new configuration version, kept among its versions as the API keeps them (R2.3.5). */
const nextVersionOf = (flow: FakeFlow, changes: Partial<FakeFlow>): FakeFlow => {
  Object.assign(flow, changes, { version: flow.version + 1 });
  flow.versions.push({
    number: flow.version,
    createdAt: new Date().toISOString(),
    configuration: {
      assets: flow.assets,
      cycleMinutes: flow.cycleMinutes,
      model: flow.model,
      instructions: flow.instructions,
      maxLeverage: flow.riskLimits.maxLeverage,
      allocatedCapital: String(flow.allocatedCapital ?? 0),
      systemPrompt: flow.systemPrompt,
      maxConsecutiveFailures: flow.maxConsecutiveFailures,
      maxDailyLossPercent: flow.maxDailyLossPercent,
      maxDrawdownPercent: flow.maxDrawdownPercent,
      openingsResume: flow.openingsResume,
      defaultStopLossPercent: flow.defaultStopLossPercent,
      defaultTakeProfitPercent: flow.defaultTakeProfitPercent,
      minimumConfidence: flow.minimumConfidence,
      memory: flow.memory,
      trailingStop: flow.trailingStop,
      consecutiveLossLimit: flow.consecutiveLossLimit,
      accountExposureForAgent: flow.accountExposureForAgent,
      feesForAgent: flow.feesForAgent,
    },
  });
  return flow;
};

/** POST /flows: a new stopped flow at version 1, or the refusal with the setting it concerns. */
export const createFlow = (user: FakeUser, request: ConfigurationRequest): FakeFlow => {
  if (request.account_id === undefined || request.account_id === '') {
    throw new InvalidRequest('account_id', 'Input should be a valid UUID');
  }
  const capital = capitalOf(request.allocated_capital);
  const name = textOf(request.name).trim();
  if (name === '') {
    throw new Refusal(422, 'nome del flusso obbligatorio', 'name');
  }
  if (user.flows.some((flow) => flow.name === name)) {
    throw new Refusal(409, 'nome già usato da un altro flusso', 'name');
  }
  const assets = assetsOf(request.assets);
  const cycleMinutes = cycleMinutesOf(request.cycle_minutes);
  const model = modelOf(user, request.model, request.model_parameters);
  const sources = sourcesOf(request.sources, user.account);
  const riskLimits = riskLimitsOf(request.max_leverage, {
    margin: request.max_margin_exposure_percent,
    value: request.max_value_exposure_percent,
    totalMargin: request.max_total_margin_exposure_percent,
    totalValue: request.max_total_value_exposure_percent,
  });
  const account = accountOf(user, textOf(request.account_id));
  requireAssetsFree(user, account.id, assets);
  const free = freeCapitalOf(user, account);
  if (capital > free) {
    throw new Refusal(
      422,
      `capitale allocato oltre il capitale libero: ${moneyText(free, CURRENCY)}`,
      'allocated_capital',
    );
  }
  return fakePlatform.addFlow(user.account, name, {
    accountName: account.name,
    status: STOPPED,
    assets,
    allocatedCapital: capital,
    cycleMinutes,
    model: model.name,
    modelParameters: model.parameters,
    sources,
    instructions: textOf(request.instructions).trim(),
    riskLimits,
    bringToMinimum: request.bring_to_minimum === true,
    systemPrompt: systemPromptOf(request.system_prompt),
    maxConsecutiveFailures:
      request.max_consecutive_failures === undefined || request.max_consecutive_failures === null
        ? null
        : maxConsecutiveFailuresOf(request.max_consecutive_failures),
    maxDailyLossPercent: maxLossOf(request.max_daily_loss_percent, 'max_daily_loss_percent'),
    maxDrawdownPercent: maxLossOf(request.max_drawdown_percent, 'max_drawdown_percent'),
    openingsResume: openingsResumeOf(request.openings_resume),
    defaultStopLossPercent: optionalTextOf(request.default_stop_loss_percent) ?? '5',
    defaultTakeProfitPercent: optionalTextOf(request.default_take_profit_percent),
    minimumConfidence: minimumConfidenceOf(request.minimum_confidence),
    memory: memoryOf(request.memory, DEFAULT_MEMORY),
    trailingStop: trailingStopOf(request.trailing_stop, DEFAULT_TRAILING_STOP),
    consecutiveLossLimit: consecutiveLossLimitOf(request.consecutive_loss_limit, null),
    accountExposureForAgent: request.account_exposure_for_agent === true,
    feesForAgent: request.fees_for_agent === true,
    currentCapital: capital,
  });
};

const flowOf = (user: FakeUser, flowId: string): FakeFlow => {
  const flow = user.flows.find((candidate) => candidate.id === flowId);
  if (flow === undefined) {
    throw new Refusal(404, 'flusso non trovato');
  }
  return flow;
};

const changed = <T>(requested: unknown, current: T, read: (value: unknown) => T): T =>
  requested === undefined || requested === null ? current : read(requested);

// The limit a modification sends, null included, or the one in force when it sends none.
const sentOr = (requested: unknown, current: string | null): unknown =>
  requested === undefined ? current : requested;

const DRAFT = 'bozza';

// The name of another flow of the user is taken (ADR nome-del-flusso-modificabile).
const renamed = (user: FakeUser, flow: FakeFlow, requested: unknown): string => {
  if (requested === undefined || requested === null) {
    return flow.name;
  }
  const name = textOf(requested).trim();
  if (name === '') {
    throw new Refusal(422, 'nome del flusso obbligatorio', 'name');
  }
  if (user.flows.some((other) => other !== flow && other.name === name)) {
    throw new Refusal(409, 'nome già usato da un altro flusso', 'name');
  }
  return name;
};

/**
 * Account and capital a modification sends: a draft takes them, within the free capital of the account; any other flow
 * keeps its own (R1.1.7, ADR bozza-configurata-dall-editor-e-duplica-con-conto).
 */
const assignmentOf = (
  user: FakeUser,
  flow: FakeFlow,
  request: ConfigurationRequest,
): Pick<FakeFlow, 'accountId' | 'allocatedCapital'> => {
  const accountId = request.account_id === undefined ? flow.accountId : textOf(request.account_id);
  const capital =
    request.allocated_capital === undefined
      ? flow.allocatedCapital
      : capitalOf(request.allocated_capital);
  if (flow.status !== DRAFT && accountId !== flow.accountId) {
    throw new Refusal(422, 'il conto di un flusso non si cambia', 'account_id');
  }
  if (flow.status !== DRAFT && capital !== flow.allocatedCapital) {
    throw new Refusal(
      422,
      'il capitale allocato di un flusso avviato si cambia con il comando del capitale',
      'allocated_capital',
    );
  }
  if (flow.status === DRAFT && accountId !== null) {
    const free = freeCapitalOf(user, accountOf(user, accountId));
    if (capital !== null && capital > free) {
      throw new Refusal(
        422,
        `capitale allocato oltre il capitale libero: ${moneyText(free, CURRENCY)}`,
        'allocated_capital',
      );
    }
  }
  return { accountId, allocatedCapital: capital };
};

// Only the name sent: the name is not part of the strategy, so the version stays (ADR nome-del-flusso-modificabile).
const nameAlone = (request: ConfigurationRequest): boolean =>
  Object.keys(request).every((key) => key === 'name');

/** PATCH /flows/{id}: only the parts sent change, as the next configuration version; a new name alone, as it is. */
export const modifyFlow = (
  user: FakeUser,
  flowId: string,
  request: ConfigurationRequest,
): FakeFlow => {
  const flow = flowOf(user, flowId);
  const name = renamed(user, flow, request.name);
  if (nameAlone(request)) {
    flow.name = name;
    return flow;
  }
  const assignment = assignmentOf(user, flow, request);
  const assets = changed(request.assets, flow.assets, assetsOf);
  const model =
    request.model === undefined && request.model_parameters === undefined
      ? { name: flow.model, parameters: flow.modelParameters }
      : modelOf(user, request.model ?? flow.model, request.model_parameters);
  const changes: Partial<FakeFlow> = {
    assets,
    cycleMinutes: changed(request.cycle_minutes, flow.cycleMinutes, cycleMinutesOf),
    model: model.name,
    modelParameters: model.parameters,
    sources: changed(request.sources, flow.sources, (requested) =>
      sourcesOf(requested, user.account),
    ),
    instructions: changed(request.instructions, flow.instructions, (value) => textOf(value).trim()),
    // A null limit of exposure sent on purpose removes it; a missing one keeps the limit in force (R1.1.3).
    riskLimits: riskLimitsOf(request.max_leverage ?? flow.riskLimits.maxLeverage, {
      margin: sentOr(request.max_margin_exposure_percent, flow.riskLimits.maxMarginExposurePercent),
      value: sentOr(request.max_value_exposure_percent, flow.riskLimits.maxValueExposurePercent),
      totalMargin: sentOr(
        request.max_total_margin_exposure_percent,
        flow.riskLimits.maxTotalMarginExposurePercent,
      ),
      totalValue: sentOr(
        request.max_total_value_exposure_percent,
        flow.riskLimits.maxTotalValueExposurePercent,
      ),
    }),
    defaultStopLossPercent:
      optionalTextOf(request.default_stop_loss_percent) ?? flow.defaultStopLossPercent,
    // A null take profit sent on purpose removes it; a missing one keeps the one in force (R3.1.2).
    defaultTakeProfitPercent:
      request.default_take_profit_percent === undefined
        ? flow.defaultTakeProfitPercent
        : optionalTextOf(request.default_take_profit_percent),
    // A null minimum confidence sent on purpose removes it; a missing one keeps the one in force (R3.1.4).
    minimumConfidence:
      request.minimum_confidence === undefined
        ? flow.minimumConfidence
        : minimumConfidenceOf(request.minimum_confidence),
    bringToMinimum: changed(
      request.bring_to_minimum,
      flow.bringToMinimum,
      (value) => value === true,
    ),
    // A null sent on purpose goes back to the default; a missing one keeps the prompt in force (R1.4.8).
    systemPrompt:
      request.system_prompt === undefined
        ? flow.systemPrompt
        : systemPromptOf(request.system_prompt),
    // A null sent on purpose removes the maximum; a missing one keeps it (R3.2.4).
    maxConsecutiveFailures:
      request.max_consecutive_failures === undefined
        ? flow.maxConsecutiveFailures
        : maxConsecutiveFailuresOf(request.max_consecutive_failures),
    // A null loss sent on purpose removes it; a missing one keeps it (R3.2.2).
    maxDailyLossPercent: maxLossOf(
      sentOr(request.max_daily_loss_percent, flow.maxDailyLossPercent),
      'max_daily_loss_percent',
    ),
    maxDrawdownPercent: maxLossOf(
      sentOr(request.max_drawdown_percent, flow.maxDrawdownPercent),
      'max_drawdown_percent',
    ),
    openingsResume:
      request.openings_resume === undefined
        ? flow.openingsResume
        : openingsResumeOf(request.openings_resume),
    memory: memoryOf(request.memory, flow.memory),
    trailingStop: trailingStopOf(request.trailing_stop, flow.trailingStop),
    consecutiveLossLimit: consecutiveLossLimitOf(
      request.consecutive_loss_limit,
      flow.consecutiveLossLimit,
    ),
    accountExposureForAgent: changed(
      request.account_exposure_for_agent,
      flow.accountExposureForAgent,
      (value) => value === true,
    ),
    feesForAgent: changed(request.fees_for_agent, flow.feesForAgent, (value) => value === true),
  };
  // A draft takes nothing on its account until it starts: the conflict on the assets waits for the start (ADR 0124).
  if (flow.status !== DRAFT) {
    requireAssetsFree(user, flow.accountId ?? '', assets, flow);
  }
  return nextVersionOf(flow, { ...changes, ...assignment, name });
};

/** PUT /flows/{id}/allocated-capital: the new capital, within what the account has free, as a new version. */
export const changeAllocatedCapital = (
  user: FakeUser,
  flowId: string,
  request: ConfigurationRequest,
): FakeFlow => {
  const flow = flowOf(user, flowId);
  const capital = capitalOf(request.allocated_capital);
  const current = flow.allocatedCapital ?? 0;
  if (capital === current) {
    return flow;
  }
  const account = accountOf(user, flow.accountId ?? '');
  const available = freeCapitalOf(user, account) + current;
  if (capital > available) {
    throw new Refusal(
      422,
      `capitale allocato oltre il capitale disponibile: ${moneyText(available, CURRENCY)}`,
      'allocated_capital',
    );
  }
  return nextVersionOf(flow, { allocatedCapital: capital });
};
