/**
 * Cycles as the API records them (R1.7.1): the steps by their Italian names and what each step produced, as the JSON
 * journal of the worker writes it. Unit tests and scenarios build them here; the fake API pages and serves them.
 */
export type FakeStepDocument = { readonly step: string; readonly content: Record<string, unknown> };

export type FakeCycle = {
  readonly planned_at: string;
  readonly started_at: string | null;
  readonly delay_seconds: number | null;
  readonly outcome: string;
  readonly failure: {
    readonly step: string;
    readonly error_type: string;
    readonly message: string;
  } | null;
  readonly steps: string[];
  readonly absent_sources: {
    readonly source: string;
    readonly reason: string;
    readonly adapter: string | null;
  }[];
  readonly documents: FakeStepDocument[];
  readonly cost: {
    readonly input_tokens: number;
    readonly output_tokens: number;
    readonly cost_usd: string | null;
  } | null;
  /** What started the cycle: its schedule, or the user who asked for it now (R6.5.2). */
  readonly trigger: 'scheduled' | 'on_demand';
  /** The memory the agent received, for every asset; null with the memory of the flow off (R5.3.4). */
  readonly memory: FakeCycleMemory[] | null;
};

/** The previous operative decisions of the flow on an asset the agent received in a cycle (R5.3.4). */
export type FakeCycleMemory = {
  readonly asset: string;
  readonly decisions: {
    readonly planned_at: string;
    readonly action: string;
    readonly direction: string | null;
    readonly price: string | null;
    readonly reasoning: string;
    readonly outcome: { readonly pnl: string; readonly realized: boolean } | null;
  }[];
};

export const STEPS = {
  readFlowState: 'lettura dello stato del flusso',
  collectSources: 'raccolta dei dati delle fonti',
  composeContext: 'composizione del contesto',
  agentDecision: "decisione dell'agente",
  riskCheck: 'controllo del rischio',
  orderExecution: 'esecuzione degli ordini',
  updateFlowState: 'aggiornamento dello stato del flusso',
  recordCycle: 'registrazione del ciclo',
} as const;

const STEP_ORDER: readonly string[] = Object.values(STEPS);

/** The instant as the API writes it: UTC, to the second. */
export const apiInstant = (instant: Date): string => instant.toISOString().replace('.000Z', 'Z');

const STATE = {
  tipo: 'FlowStateView',
  currency: 'USDC',
  allocated_capital: '500',
  funds: '500',
  available_liquidity: '500',
  total_value: '500',
  return_percent: '0.00',
  positions: [],
};

/** The exit plan of an opening as the journal records it (R3.1.1): prices as decimal strings, null when not given. */
export type FakeExitPlan = {
  readonly target: string | null;
  readonly stop: string | null;
  readonly invalidation: string | null;
};

const NO_EXIT_PLAN: FakeExitPlan = { target: null, stop: null, invalidation: null };

export const reasoningOf = (asset: string) =>
  `RSI di ${asset} in risalita da 28 e previsione a un'ora sopra il prezzo: apro long con margine contenuto.`;

// How convinced of its decision the agent is, from 0 to 100, as the journal records it (R3.1.4).
const CONFIDENCE = 75;

const documentsOf = (
  asset: string,
  exitPlan: FakeExitPlan,
  confidence: number,
): FakeStepDocument[] => [
  {
    step: STEPS.readFlowState,
    content: {
      flusso: 'alfa',
      conto: 'test-1',
      ambiente: 'dev',
      modello: 'openai/gpt-4o',
      stato: STATE,
    },
  },
  {
    step: STEPS.collectSources,
    content: {
      fonti: [
        {
          fonte: 'indicatori',
          dati: [{ tipo: 'SourceData', source: 'indicatori', asset, values: { rsi_14: '31.4' } }],
        },
        {
          fonte: 'forecast',
          dati: [
            { tipo: 'SourceData', source: 'forecast', asset, values: { prezzo_tra_1h: '97250.5' } },
          ],
        },
      ],
    },
  },
  {
    step: STEPS.composeContext,
    content: {
      messaggi: [
        { ruolo: 'system', contenuto: 'Sei il gestore del flusso alfa.' },
        { ruolo: 'user', contenuto: `Dati di ${asset}: RSI 31.4, previsione a 1h 97250.5` },
      ],
    },
  },
  {
    step: STEPS.agentDecision,
    content: {
      risposta: `{"decisions": [{"asset": "${asset}", "action": "open", "direction": "long"}]}`,
      decisioni: [
        {
          tipo: 'Decision',
          asset,
          action: 'apri',
          reasoning: reasoningOf(asset),
          confidence,
          opening: {
            tipo: 'TradeOpening',
            direction: 'long',
            margin_fraction: '0.1',
            leverage: 2,
            exit_plan: { tipo: 'ExitPlan', ...exitPlan },
          },
        },
      ],
      scartate: [],
      mancanti: [],
    },
  },
  {
    step: STEPS.riskCheck,
    content: {
      esiti: [
        {
          tipo: 'ApprovedOpening',
          asset,
          side: 'buy',
          value: '100',
          leverage: 2,
          adjustments: [],
        },
      ],
      ordini_approvati: 1,
    },
  },
  {
    step: STEPS.orderExecution,
    content: {
      risultato: [{ order_id: '91', status: 'eseguito', coin: asset, filled_size: '0.001' }],
    },
  },
  { step: STEPS.updateFlowState, content: { stato: STATE } },
];

/**
 * A cycle that ran every step and opened a long position on the asset, with the exit plan and the confidence the agent
 * gave.
 */
export const aCompletedCycle = (
  plannedAt: Date,
  asset = 'BTC',
  exitPlan: FakeExitPlan = NO_EXIT_PLAN,
  confidence = CONFIDENCE,
): FakeCycle => ({
  planned_at: apiInstant(plannedAt),
  started_at: apiInstant(new Date(plannedAt.getTime() + 2000)),
  delay_seconds: 2,
  outcome: 'concluso',
  failure: null,
  steps: [...STEP_ORDER],
  absent_sources: [],
  documents: documentsOf(asset, exitPlan, confidence),
  cost: { input_tokens: 1200, output_tokens: 300, cost_usd: '0.0125' },
  trigger: 'scheduled',
  memory: null,
});

/** The same cycle stopped at the step: it keeps only what the steps before it produced (R1.2.3). */
export const aFailedCycle = (
  cycle: FakeCycle,
  step: string,
  failure: { errorType: string; message: string },
): FakeCycle => {
  const ran = STEP_ORDER.slice(0, STEP_ORDER.indexOf(step));
  return {
    ...cycle,
    outcome: 'fallito',
    failure: { step, error_type: failure.errorType, message: failure.message },
    steps: ran,
    documents: cycle.documents.filter((document) => ran.includes(document.step)),
    cost: null,
  };
};

/** A decision of the agent as the journal records it: the direction only in the fields of an opening (R1.4.4). */
export type FakeDecision = {
  readonly asset: string;
  readonly action: string;
  readonly reasoning: string;
  readonly confidence?: number;
  readonly opening?: { readonly direction: string } | null;
};

/** The same cycle with other decisions of the agent in the document of its decision (R6.5.4). */
export const withDecisions = (cycle: FakeCycle, decisions: FakeDecision[]): FakeCycle => ({
  ...cycle,
  documents: cycle.documents.map((document) =>
    document.step === STEPS.agentDecision
      ? { ...document, content: { ...document.content, decisioni: decisions } }
      : document,
  ),
});

/** The summary of the cycle in the list, as the API gives it (R1.7.3). */
export const summaryOf = (cycle: FakeCycle) => ({
  planned_at: cycle.planned_at,
  started_at: cycle.started_at,
  outcome: cycle.outcome,
  failure: cycle.failure,
  decisions:
    cycle.documents.find((document) => document.step === STEPS.agentDecision)?.content ?? null,
  trigger: cycle.trigger,
});
