/** The catalogs of the fake platform, as the API describes them: each model and source with its parameters. */
export type FakeModelParameter = {
  readonly key: string;
  readonly label: string;
  readonly default: string;
  readonly minimum?: string;
  readonly maximum?: string;
  readonly whole?: boolean;
  readonly choices?: string[];
};

export type FakeModel = {
  readonly name: string;
  readonly provider: string;
  readonly parameters: FakeModelParameter[];
};

export type FakeSourceParameter = {
  readonly key: string;
  readonly label: string;
  readonly default: number;
  readonly minimum: number;
  readonly maximum: number;
  // Empty for a parameter that admits its whole range (ADR orizzonti-lunghi-del-forecast).
  readonly choices: readonly { readonly value: number; readonly label: string }[];
};

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

const SERIES_LENGTH: FakeSourceParameter = {
  key: 'lunghezza_serie',
  label: 'lunghezza serie',
  default: 10,
  minimum: 1,
  maximum: 50,
  choices: [],
};
const NEWS_COUNT: FakeSourceParameter = {
  key: 'numero_notizie',
  label: 'numero notizie',
  default: 10,
  minimum: 1,
  maximum: 50,
  choices: [],
};
const HISTORY_DAYS: FakeSourceParameter = {
  key: 'profondita_storico_giorni',
  label: 'profondità storico giorni',
  default: 7,
  minimum: 1,
  maximum: 90,
  choices: [],
};
const LONG_HORIZON: FakeSourceParameter = {
  key: 'orizzonte_lungo',
  label: 'orizzonte lungo',
  default: 0,
  minimum: 0,
  maximum: 10080,
  choices: [
    { value: 0, label: 'nessuno' },
    { value: 1440, label: '1 giorno' },
    { value: 10080, label: '1 settimana' },
  ],
};

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
      },
      {
        key: 'reasoning_effort',
        label: 'livello di ragionamento',
        default: 'medium',
        choices: ['low', 'medium', 'high'],
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
    parameters: [SERIES_LENGTH],
    adapters: [
      adapterOf('Hyperliquid', 'Dati di mercato pubblici di Hyperliquid.', [SERIES_LENGTH], true),
    ],
  },
  {
    name: 'forecast',
    description:
      'Previsione del prezzo a 15 minuti e a 1 ora e, a scelta, a 1 giorno o a 1 settimana.',
    per_asset: true,
    parameters: [HISTORY_DAYS, LONG_HORIZON],
    adapters: [
      adapterOf(
        'Prophet',
        'Previsione di Prophet dal servizio forecaster.',
        [HISTORY_DAYS, LONG_HORIZON],
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
