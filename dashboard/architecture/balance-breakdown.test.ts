// ADR-scomposizione-del-saldo-nel-riquadro-del-conto (Bug 601): the box of the account shows the value of the flows and
// their result as the API gives them, beside the free capital. The dashboard reads both fields of the free capital and
// never works out the result of the flows from the capital allocated: that arithmetic is the API's (ADR 0116).
import { readdirSync, readFileSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

const ACCOUNTS = fileURLToPath(new URL('../src/features/accounts', import.meta.url));
const FREE_CAPITAL_API = 'api/get-free-capital.ts';

type SourceFile = { readonly path: string; readonly source: string };

const sourcesOf = (directory: string): SourceFile[] =>
  readdirSync(directory, { recursive: true, encoding: 'utf8' })
    .filter((path) => /\.tsx?$/.test(path) && !/\.test\.tsx?$/.test(path))
    .map((path) => relative(directory, join(directory, path)).split(sep).join('/'))
    .map((path) => ({ path, source: readFileSync(join(directory, path), 'utf8') }));

const BREAKDOWN_FIELDS = ['flows_value', 'flows_result'] as const;

const FIELD = String.raw`\b(?:flows_value|flows_result|allocated_capital)\b`;
// A number made of a field of the breakdown, or a field of it summed or taken off another value.
const ARITHMETIC = new RegExp(
  String.raw`Number\([^)]*${FIELD}|${FIELD}\)?\s*[-+*/]\s*[\w(]|[\w)]\s*[-+*/]\s*[\w.]*${FIELD}`,
);

/** The fields of the breakdown the API of the free capital does not read from the response. */
const fieldsNotRead = (files: readonly SourceFile[]): string[] => {
  const api = files.find((file) => file.path === FREE_CAPITAL_API);
  if (api === undefined) {
    return [`${FREE_CAPITAL_API}: mancante`];
  }
  return BREAKDOWN_FIELDS.filter((field) => !api.source.includes(field)).map(
    (field) => `${FREE_CAPITAL_API}: non legge ${field}`,
  );
};

/** The files of the feature that compute with the value, the result or the capital of the flows. */
const breakdownComputedByTheDashboard = (files: readonly SourceFile[]): string[] =>
  files.filter((file) => ARITHMETIC.test(file.source)).map((file) => file.path);

const file = (path: string, source: string): SourceFile => ({ path, source });

const CONFORMING_API = file(
  FREE_CAPITAL_API,
  'z.object({ amount: z.string(), currency: z.string(), flows_value: z.string(), flows_result: z.string() })',
);

describe('ADR-scomposizione-del-saldo-nel-riquadro-del-conto: the breakdown comes from the API', () => {
  it('is red when the API of the free capital does not read the result of the flows', () => {
    const api = file(FREE_CAPITAL_API, 'z.object({ amount: z.string(), flows_value: z.string() })');

    expect(fieldsNotRead([api])).toEqual([`${FREE_CAPITAL_API}: non legge flows_result`]);
  });

  it('is red when the API of the free capital is missing', () => {
    expect(fieldsNotRead([])).toEqual([`${FREE_CAPITAL_API}: mancante`]);
  });

  it('is silent when the API of the free capital reads both fields', () => {
    expect(fieldsNotRead([CONFORMING_API])).toEqual([]);
  });

  it('finds both fields read by the API of the free capital', () => {
    expect(fieldsNotRead(sourcesOf(ACCOUNTS))).toEqual([]);
  });
});

describe('ADR-scomposizione-del-saldo-nel-riquadro-del-conto: the dashboard computes nothing of it', () => {
  it.each([
    ['Number(capital.flows_value) - Number(account.allocated_capital)'],
    ['capital.flows_value - account.allocated_capital'],
    ['balance - capital.flows_value'],
    ['String(Number(account.allocated_capital))'],
  ])('is red when a component computes %s', (expression) => {
    const files = [file('components/flows-value.tsx', `const result = ${expression};`)];

    expect(breakdownComputedByTheDashboard(files)).toEqual(['components/flows-value.tsx']);
  });

  it('is silent when a component shows the fields as the API gives them', () => {
    const files = [
      file(
        'components/flows-value.tsx',
        '`capitale allocato ${formatAmount(account.allocated_capital)}`; formatSignedAmount(capital.flows_result);',
      ),
    ];

    expect(breakdownComputedByTheDashboard(files)).toEqual([]);
  });

  it('finds no arithmetic on the breakdown in the feature accounts', () => {
    expect(breakdownComputedByTheDashboard(sourcesOf(ACCOUNTS))).toEqual([]);
  });
});
