import { fakeClock } from './clock';

/** A trial as the API answers it: what the adapter read, or why it read nothing (R6.3.1). */
export type FakeSourceTrial = {
  readonly outcome: 'succeeded' | 'failed';
  readonly values: { readonly reference_at: string; readonly values: Record<string, string> }[];
  readonly data_at: string | null;
  readonly response_milliseconds: number;
  readonly reason: string | null;
  readonly permanent: boolean;
};

/** A trial the worker of the fake platform ran: the request as it reached it. */
export type FakeTrialRequest = {
  readonly account: string;
  readonly source: string;
  readonly adapter: string;
  readonly asset: string | null;
  readonly parameters: Readonly<Record<string, number>>;
};

/** How long the sources of the fake platform take to answer, and the age of the data they read. */
export const FAKE_TRIAL_MILLISECONDS = 184;
const DATA_AGE_MS = 5 * 60_000;

const state = {
  // The sources that do not answer: their trial fails, transient, as a source a cycle waits for in vain (R1.2.5).
  silent: new Set<string>(),
  requests: [] as FakeTrialRequest[],
};

/** The reason the API gives for a source that does not answer (R1.2.5). */
export const unreachableReason = (source: string): string => `fonte non raggiungibile: ${source}`;

const valuesOf = (request: FakeTrialRequest): Record<string, string> => ({
  ...(request.asset === null ? {} : { asset: request.asset }),
  ...Object.fromEntries(
    Object.entries(request.parameters).map(([key, value]) => [key, String(value)]),
  ),
  valore: '42',
});

/** The worker of the fake platform when it tries an adapter of a source (R6.3.1). */
export const fakeSourceTrials = {
  reset(): void {
    state.silent.clear();
    state.requests = [];
  },

  silence(source: string): void {
    state.silent.add(source);
  },

  /** Every trial the worker ran, in order: a refused one never reaches it. */
  requests(): readonly FakeTrialRequest[] {
    return state.requests;
  },

  run(request: FakeTrialRequest): FakeSourceTrial {
    state.requests.push(request);
    if (state.silent.has(request.source)) {
      return {
        outcome: 'failed',
        values: [],
        data_at: null,
        response_milliseconds: FAKE_TRIAL_MILLISECONDS,
        reason: unreachableReason(request.source),
        permanent: false,
      };
    }
    const referenceAt = new Date(fakeClock.now() - DATA_AGE_MS).toISOString();
    return {
      outcome: 'succeeded',
      values: [{ reference_at: referenceAt, values: valuesOf(request) }],
      data_at: referenceAt,
      response_milliseconds: FAKE_TRIAL_MILLISECONDS,
      reason: null,
      permanent: false,
    };
  },
};
