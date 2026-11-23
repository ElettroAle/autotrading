// ADR-card-condivisa-distinta-dallo-sfondo (Bug 726): a box of a feature or a route is the shared Card of
// src/components/ui/card.tsx, filled apart from the background of the page. No feature and no route writes a container
// with a border and an inner padding without a background: the rule of eslint.architecture.js is red on one, silent on a
// conforming one.
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

const FEATURE = 'src/features/source-trials/components/source-trials-list.tsx';
const ROUTE = 'src/app/routes/app/sources.tsx';

describe('ADR-card-condivisa-distinta-dallo-sfondo: a box of a page stands apart from its background', () => {
  it.each([
    [
      'a feature writes a box with a border and a padding, without a background',
      FEATURE,
      'export const Box = () => <article className="space-y-3 rounded border border-slate-200 p-4" />;\n',
    ],
    [
      'a route writes such a box',
      ROUTE,
      'export const Box = () => <div className="p-3 border rounded" />;\n',
    ],
    [
      'a feature writes the box with a thick border',
      FEATURE,
      'export const Box = () => <section className="rounded border-2 border-slate-200 p-4" />;\n',
    ],
    [
      'a feature writes the classes of the box in a constant',
      FEATURE,
      "const BOX = 'rounded border border-slate-200 p-4';\nexport const look = BOX;\n",
    ],
    [
      'a feature writes the classes of the box in a template',
      FEATURE,
      'export const lookOf = (gap) => `${gap} rounded border border-slate-200 p-4`;\n',
    ],
  ])('is red when %s', async (_case, path, source) => {
    expect(await brokenRules(path, source)).toContain(RULE);
  });

  it.each([
    [
      'a feature uses the shared card',
      FEATURE,
      'import { Card } from \'@/components/ui/card\';\nexport const Box = () => <Card as="article" className="space-y-3" />;\n',
    ],
    [
      'a feature writes a box of warning with its own colour',
      FEATURE,
      'export const Notice = () => <p className="rounded border border-amber-300 bg-amber-50 p-2" />;\n',
    ],
    [
      'a feature writes a command with a border and a horizontal padding',
      FEATURE,
      'export const Command = () => <button className="rounded border border-slate-300 px-3 py-1.5" />;\n',
    ],
    [
      'a feature writes a padding with a border on one side only',
      FEATURE,
      'export const Row = () => <div className="border-b border-slate-200 p-2" />;\n',
    ],
    [
      'the shared components write the box',
      'src/components/ui/card.tsx',
      "const BOX = 'rounded-lg border p-4 shadow-sm';\nexport const look = BOX;\n",
    ],
    [
      'a test of a feature writes such a box',
      'src/features/source-trials/components/source-trials.test.tsx',
      'export const Box = () => <div className="rounded border p-4" />;\n',
    ],
  ])('is silent when %s', async (_case, path, source) => {
    expect(await brokenRules(path, source)).toEqual([]);
  });
});
