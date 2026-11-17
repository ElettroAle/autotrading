// ADR-mancanze-della-bozza-dichiarate-dall-api (Bug 560): what a draft lacks to start comes from the API; the dashboard
// keeps no copy of the rule of the domain, so no code tells a missing part from an empty field.
import { readdirSync, readFileSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

const SOURCES = fileURLToPath(new URL('../src', import.meta.url));

type SourceFile = { readonly path: string; readonly source: string };

const isTest = (path: string): boolean => /\.test\.tsx?$/.test(path);

// The fakes of the API answer as the API does on purpose: they are not the dashboard.
const sourcesOf = (directory: string): SourceFile[] =>
  readdirSync(directory, { recursive: true, encoding: 'utf8' })
    .filter((path) => /\.tsx?$/.test(path) && !isTest(path))
    .map((path) => relative(directory, join(directory, path)).split(sep).join('/'))
    .filter((path) => !path.startsWith('testing/') && !path.endsWith('.d.ts'))
    .map((path) => ({ path, source: readFileSync(join(directory, path), 'utf8') }));

const FLOWS_SCHEMA = 'features/flows/api/get-flows.ts';

// An empty field turned into the name of a missing part: the rule of the domain copied.
const COPY_OF_THE_RULE = /(=== null|\.length === 0)\s*\?\s*'(conto|capitale allocato|asset)'/;
const MISSING_FROM_THE_API = /missing: z\.array\(z\.string\(\)\)/;

/** The files that copy the rule, and the schema of the flows when it does not read what the API declares missing. */
const copiesOfTheRule = (files: readonly SourceFile[]): string[] => [
  ...files.filter((file) => COPY_OF_THE_RULE.test(file.source)).map((file) => file.path),
  ...files
    .filter((file) => file.path === FLOWS_SCHEMA && !MISSING_FROM_THE_API.test(file.source))
    .map((file) => `${file.path}: non legge missing`),
];

const file = (path: string, source: string): SourceFile => ({ path, source });

const schema = file(FLOWS_SCHEMA, 'missing: z.array(z.string()),');

describe('ADR-mancanze-della-bozza-dichiarate-dall-api: the API declares what a draft lacks', () => {
  it('is red when a component computes what the draft lacks from its fields', () => {
    const files = [
      schema,
      file(
        'features/flows/components/draft-readiness.tsx',
        "[flow.account_id === null ? 'conto' : '', flow.assets.length === 0 ? 'asset' : '']",
      ),
    ];

    expect(copiesOfTheRule(files)).toEqual(['features/flows/components/draft-readiness.tsx']);
  });

  it('is red when the schema of the flows does not read what the API declares missing', () => {
    expect(copiesOfTheRule([file(FLOWS_SCHEMA, 'assets: z.array(z.string()),')])).toEqual([
      `${FLOWS_SCHEMA}: non legge missing`,
    ]);
  });

  it('is silent when the components read what the API declares', () => {
    const files = [
      schema,
      file('features/flows/components/draft-readiness.tsx', '<p>{readinessOf(flow.missing)}</p>'),
    ];

    expect(copiesOfTheRule(files)).toEqual([]);
  });

  it('finds no copy of the rule in the dashboard', () => {
    expect(copiesOfTheRule(sourcesOf(SOURCES))).toEqual([]);
  });
});
