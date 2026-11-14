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
};

export type FakeSource = {
  readonly name: string;
  readonly description: string;
  readonly per_asset: boolean;
  readonly parameters: FakeSourceParameter[];
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
    parameters: [
      { key: 'lunghezza_serie', label: 'lunghezza serie', default: 10, minimum: 1, maximum: 50 },
    ],
  },
  {
    name: 'sentiment',
    description: 'Indice Fear and Greed delle criptovalute.',
    per_asset: false,
    parameters: [],
  },
  {
    name: 'notizie',
    description: 'Le notizie recenti sugli asset del flusso.',
    per_asset: true,
    parameters: [
      { key: 'numero_notizie', label: 'numero notizie', default: 10, minimum: 1, maximum: 50 },
    ],
  },
];
