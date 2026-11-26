/** The catalogs of the fake platform, as the API describes them: each model and source with its parameters. */
export type FakeModelParameter = {
  readonly key: string;
  readonly label: string;
  readonly default: string;
  readonly minimum?: string;
  readonly maximum?: string;
  readonly whole?: boolean;
  readonly choices?: string[];
  // What the parameter does, as the platform describes it: the text of its info button (R5.5.7).
  readonly description: string;
};

export type FakeModel = {
  readonly name: string;
  readonly provider: string;
  readonly parameters: FakeModelParameter[];
};

export type FakeSourceParameter = {
  readonly key: string;
  readonly label: string;
  // A whole number, or a list of them each in the range (ADR parametri-delle-fonti-come-liste-libere).
  readonly kind: 'number' | 'list';
  readonly default: number | readonly number[];
  readonly minimum: number;
  readonly maximum: number;
  // Empty for a parameter that admits its whole range (ADR orizzonti-lunghi-del-forecast).
  readonly choices: readonly { readonly value: number; readonly label: string }[];
  // How many values a list admits; none for a whole number.
  readonly maximum_values: number | null;
  // What the parameter does, what it admits and its default, as its declaration says: the text of its info button
  // (R5.5.7).
  readonly description: string;
};

/** A whole number parameter of a source, as the API declares it, with the description of its info button. */
export const numberParameter = (
  key: string,
  label: string,
  [defaultValue, minimum, maximum]: readonly [number, number, number],
): FakeSourceParameter => ({
  key,
  label,
  kind: 'number',
  default: defaultValue,
  minimum,
  maximum,
  choices: [],
  maximum_values: null,
  description: `Valore di ${label}. Da ${minimum} a ${maximum}. Predefinito: ${defaultValue}.`,
});

/** A list parameter of a source, as the API declares it, with at most 8 values and the description of its info button. */
export const listParameter = (
  key: string,
  label: string,
  defaultValues: readonly number[],
  [minimum, maximum]: readonly [number, number],
): FakeSourceParameter => ({
  key,
  label,
  kind: 'list',
  default: defaultValues,
  minimum,
  maximum,
  choices: [],
  maximum_values: 8,
  description: `Valori di ${label}. Da ${minimum} a ${maximum}, al massimo 8 valori. Vuoto: nessun valore.`,
});

/** An adapter of a source as it declares itself; no configuration field means none needed (R4.1.1). */
export type FakeSourceAdapter = {
  readonly name: string;
  readonly description: string;
  readonly parameters: FakeSourceParameter[];
  readonly configuration_fields: {
    readonly name: string;
    readonly label: string;
    readonly secret: boolean;
  }[];
  readonly offers_history: boolean;
};

export type FakeSource = {
  readonly name: string;
  readonly description: string;
  readonly per_asset: boolean;
  readonly parameters: FakeSourceParameter[];
  readonly adapters: FakeSourceAdapter[];
};

const adapterOf = (
  name: string,
  description: string,
  parameters: FakeSourceParameter[],
  offersHistory: boolean,
): FakeSourceAdapter => ({
  name,
  description,
  parameters,
  configuration_fields: [],
  offers_history: offersHistory,
});

const SERIES_LENGTH = numberParameter('lunghezza_serie', 'lunghezza serie', [10, 1, 50]);
const AVERAGE_PERIODS = listParameter('medie_periodi', 'medie periodi', [20, 50], [2, 10000]);
const RSI_PERIODS: FakeSourceParameter = {
  ...listParameter('rsi_periodi', 'rsi periodi', [7, 14], [2, 10000]),
  description:
    "Periodi in candele dell'RSI, uno per periodo. Da 2 a 10000, al massimo 8 valori. Predefinito: 7, 14; vuoto: nessun RSI.",
};
const TREND_DAYS = listParameter('tendenza_giorni', 'tendenza giorni', [], [1, 3650]);
const NEWS_COUNT = numberParameter('numero_notizie', 'numero notizie', [10, 1, 50]);
const HISTORY_DAYS = numberParameter(
  'profondita_storico_giorni',
  'profondità storico giorni',
  [7, 1, 90],
);
const HORIZONS = listParameter('orizzonti_minuti', 'orizzonti minuti', [15, 60], [15, 43200]);
// The regime data the adapter of the market declares for the indicators only (R5.5.4).
const REGIME_PARAMETERS = [
  listParameter('estremi_ore', 'estremi_ore', [], [1, 720]),
  listParameter('variazione_ore', 'variazione_ore', [], [1, 720]),
  numberParameter('serie_chiusure', 'serie_chiusure', [0, 0, 1]),
];

/** The assets the exchange of the fake installation trades now, as the API lists them: by name (ADR 0147). */
export const FAKE_TRADABLE_ASSETS: readonly string[] = ['BTC', 'ETH', 'SOL'];

/** The default system prompt of the fake platform and the placeholders it declares (R1.4.8). */
export const FAKE_SYSTEM_PROMPT = {
  system_prompt: '{instructions}\n\nRegole operative:\n- leva da 1 a {max_leverage} su {assets}',
  system_prompt_placeholders: [
    { name: 'instructions', description: "le istruzioni dell'agente del flusso" },
    { name: 'actions', description: 'le azioni ammesse per ogni asset' },
    { name: 'max_leverage', description: 'la leva massima del flusso' },
    { name: 'assets', description: 'gli asset del flusso' },
  ],
};

const TEMPERATURE: FakeModelParameter = {
  key: 'temperature',
  label: 'temperatura',
  default: '1',
  minimum: '0',
  maximum: '2',
  whole: false,
  description:
    "Quanto variano le risposte del modello: più bassa, risposte più ripetibili; più alta, più varie. Un numero nell'intervallo che il modello ammette. Vuoto: il valore predefinito del modello, mostrato nel campo.",
};

export const FAKE_MODELS: FakeModel[] = [
  {
    name: 'openrouter/deepseek-chat',
    provider: 'openrouter',
    parameters: [
      TEMPERATURE,
      {
        key: 'max_tokens',
        label: 'limite di lunghezza della risposta',
        default: '4096',
        minimum: '1',
        maximum: '8192',
        whole: true,
        description:
          "Lunghezza massima della risposta del modello, in token: una risposta più lunga si interrompe. Un intero nell'intervallo che il modello ammette. Vuoto: il valore predefinito del modello, mostrato nel campo.",
      },
      {
        key: 'reasoning_effort',
        label: 'livello di ragionamento',
        default: 'medium',
        choices: ['low', 'medium', 'high'],
        description:
          'Quanto ragiona il modello prima di rispondere: più ragionamento dà risposte più meditate, più lente e più costose. Uno dei livelli che il modello ammette. Vuoto: il livello predefinito del modello.',
      },
    ],
  },
  { name: 'openai/gpt-4o', provider: 'openai', parameters: [TEMPERATURE] },
  { name: 'anthropic/claude-sonnet', provider: 'anthropic', parameters: [TEMPERATURE] },
  // A name as long as the longest of a real catalog: the form must hold it on a phone (ADR 0146).
  {
    name: 'openrouter/nvidia/llama-3.1-nemotron-ultra-253b-v1-instruct-extended-reasoning-preview',
    provider: 'openrouter',
    parameters: [TEMPERATURE],
  },
];

export const FAKE_SOURCES: FakeSource[] = [
  {
    name: 'indicatori',
    description: 'Prezzo e indicatori tecnici su due timeframe.',
    per_asset: true,
    parameters: [SERIES_LENGTH, AVERAGE_PERIODS, RSI_PERIODS, TREND_DAYS],
    adapters: [
      adapterOf(
        'Hyperliquid',
        'Dati di mercato pubblici di Hyperliquid.',
        [SERIES_LENGTH, AVERAGE_PERIODS, RSI_PERIODS, TREND_DAYS, ...REGIME_PARAMETERS],
        true,
      ),
    ],
  },
  {
    name: 'forecast',
    description: 'Previsione del prezzo agli orizzonti in minuti scelti dal flusso.',
    per_asset: true,
    parameters: [HISTORY_DAYS, HORIZONS],
    adapters: [
      adapterOf(
        'Prophet',
        'Previsione di Prophet dal servizio forecaster.',
        [HISTORY_DAYS, HORIZONS],
        true,
      ),
    ],
  },
  {
    name: 'sentiment',
    description: 'Indice Fear and Greed delle criptovalute.',
    per_asset: false,
    parameters: [],
    adapters: [
      adapterOf('alternative.me', 'Crypto Fear & Greed Index di alternative.me.', [], true),
      adapterOf('CoinMarketCap', 'CMC Crypto Fear and Greed Index di CoinMarketCap.', [], false),
    ],
  },
  {
    name: 'notizie',
    description: 'Le notizie recenti sugli asset del flusso.',
    per_asset: true,
    parameters: [NEWS_COUNT],
    adapters: [adapterOf('RSS', 'Feed RSS delle testate cripto.', [NEWS_COUNT], false)],
  },
];
