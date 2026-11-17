let fixed: number | undefined;

/**
 * The clock of the fake API: the real time, or the instant a scenario fixed, so the periods of the last minutes read
 * the same minutes whatever the time the scenario runs (ADR periodi-brevi-nel-selettore-condiviso).
 */
export const fakeClock = {
  now: (): number => fixed ?? Date.now(),
  fix: (instant: Date): void => {
    fixed = instant.getTime();
  },
  release: (): void => {
    fixed = undefined;
  },
};
