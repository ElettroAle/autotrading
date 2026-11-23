// ADR-intervallo-delle-liste-fissato-alla-scelta-del-periodo (Bug 716): a list counts its period from the instant it
// receives the period, through useListInterval of src/components/ui/period-selector/use-period.ts. No feature and no
// route reads the clock in its render to compute an interval: the rule of eslint.architecture.js is red on one, silent
// on a conforming one.
import { fileURLToPath } from 'node:url';

import { ESLint } from 'eslint';
import { beforeAll, describe, expect, it } from 'vitest';

const DASHBOARD = fileURLToPath(new URL('..', import.meta.url));
const RULE = 'no-restricted-syntax';

// Only the rule under proof runs: the import rules would load the resolver of the whole dashboard for nothing.
const architecture = new ESLint({
  cwd: DASHBOARD,
  overrideConfigFile: 'eslint.architecture.js',
  ruleFilter: ({ ruleId }) => ruleId === RULE,
});

const brokenRules = async (path: string, source: string): Promise<string[]> => {
  const [result] = await architecture.lintText(source, { filePath: `${DASHBOARD}${path}` });
  return (result?.messages ?? []).map((message) => message.ruleId ?? message.message);
};

const WARM_UP_TIMEOUT_MS = 60_000;

// The first lint loads the configuration and the parser, a fixed cost of seconds on a busy machine: it is paid once
// here, so no proof below is timed on it.
beforeAll(async () => {
  await brokenRules('src/features/warm-up/warm-up.ts', 'export {};\n');
}, WARM_UP_TIMEOUT_MS);

const LIST = 'src/features/cycles/components/cycles-list.tsx';
const ROUTE = 'src/app/routes/app/flow.tsx';
const PERIOD_SELECTOR = "from '@/components/ui/period-selector/use-period';\n";

describe('ADR-intervallo-delle-liste-fissato-alla-scelta-del-periodo: the interval of a list', () => {
  it.each([
    [
      'a feature computes the interval of a list from now',
      LIST,
      `import { listIntervalOf } ${PERIOD_SELECTOR}export const interval = (period) => listIntervalOf(period, new Date());\n`,
    ],
    [
      'a feature computes the interval under another name',
      LIST,
      `import { listIntervalOf as intervalOf } ${PERIOD_SELECTOR}export const interval = intervalOf;\n`,
    ],
    ['a feature reads the clock in its render', LIST, 'export const now = () => new Date();\n'],
    ['a feature reads the time of now', LIST, 'export const now = () => Date.now();\n'],
    ['a route reads the clock in its render', ROUTE, 'export const now = () => new Date();\n'],
  ])('is red when %s', async (_case, path, source) => {
    expect(await brokenRules(path, source)).toContain(RULE);
  });

  it.each([
    [
      'a feature takes the interval fixed when the period was chosen',
      LIST,
      `import { useListInterval } ${PERIOD_SELECTOR}export const useInterval = (period) => useListInterval(period);\n`,
    ],
    [
      'a feature reads an instant it was given',
      LIST,
      'export const instantOf = (text) => new Date(text);\n',
    ],
    [
      'the shared selector of the period computes the interval from now',
      'src/components/ui/period-selector/use-period.ts',
      'export const now = () => new Date();\n',
    ],
    [
      'a test moves the clock of a feature',
      'src/features/cycles/components/cycles-list.test.tsx',
      `import { listIntervalOf } ${PERIOD_SELECTOR}export const now = () => listIntervalOf(period, new Date(Date.now()));\n`,
    ],
  ])('is silent when %s', async (_case, path, source) => {
    expect(await brokenRules(path, source)).toEqual([]);
  });
});
