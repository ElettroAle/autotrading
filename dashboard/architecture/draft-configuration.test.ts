// ADR-assegnazione-della-bozza-nel-form-di-configurazione and ADR-nome-del-flusso-modificabile: account, capital and
// assets of a draft are set only in the form of the configuration, saved with the modification of the flow; no other
// code assigns a draft, and the name in that form is not fixed.
import { readdirSync, readFileSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

const SOURCES = fileURLToPath(new URL('../src', import.meta.url));

type SourceFile = { readonly path: string; readonly source: string };

const isTest = (path: string): boolean => /\.test\.tsx?$/.test(path);

const sourcesOf = (directory: string): SourceFile[] =>
  readdirSync(directory, { recursive: true, encoding: 'utf8' })
    .filter((path) => /\.tsx?$/.test(path) && !isTest(path))
    .map((path) => relative(directory, join(directory, path)).split(sep).join('/'))
    .filter((path) => !path.endsWith('.d.ts'))
    .map((path) => ({ path, source: readFileSync(join(directory, path), 'utf8') }));

const FORM = 'features/flow-editor/components/flow-form.tsx';
// A second way in: a request of the assignment, or a form of its own.
const SECOND_WAY_IN = /\/assignment'|Assegnazione della bozza/;
// The name fixed in the form: read only, or a property that makes it so.
const FIXED_NAME = /nameFixed|readOnly=\{[^}]*name/i;

/** The files with a second way in for the assignment of a draft, and the form with a fixed name. */
const outsideTheConfiguration = (files: readonly SourceFile[]): string[] => [
  ...files.filter((file) => SECOND_WAY_IN.test(file.source)).map((file) => file.path),
  ...files
    .filter((file) => file.path === FORM && FIXED_NAME.test(file.source))
    .map((file) => `${file.path}: nome fisso`),
];

const file = (path: string, source: string): SourceFile => ({ path, source });

describe('ADR-assegnazione-della-bozza-nel-form-di-configurazione: the configuration is the one way in', () => {
  it('is red when a feature sends the assignment of a draft on its own route', () => {
    const files = [
      file(
        'features/flows/api/assign-draft-flow.ts',
        "api.PUT('/flows/{flow_id}/assignment', { params })",
      ),
      file(
        'features/flows/components/draft-assignment-form.tsx',
        'aria-label="Assegnazione della bozza"',
      ),
    ];

    expect(outsideTheConfiguration(files)).toEqual([
      'features/flows/api/assign-draft-flow.ts',
      'features/flows/components/draft-assignment-form.tsx',
    ]);
  });

  it('is silent when the draft is configured with the modification of the flow', () => {
    const files = [
      file(
        'features/flow-editor/api/save-flow.ts',
        "api.PATCH('/flows/{flow_id}', { params, body })",
      ),
    ];

    expect(outsideTheConfiguration(files)).toEqual([]);
  });

  it('finds no second way in for the assignment of a draft', () => {
    expect(outsideTheConfiguration(sourcesOf(SOURCES))).toEqual([]);
  });
});

describe('ADR-nome-del-flusso-modificabile: the name is changed in the configuration', () => {
  it('is red when the form fixes the name', () => {
    const files = [file(FORM, "<input {...register('name')} readOnly={nameFixed} />")];

    expect(outsideTheConfiguration(files)).toEqual([`${FORM}: nome fisso`]);
  });

  it('is silent when the form lets the name change', () => {
    const files = [file(FORM, "<input {...control} {...register('name')} />")];

    expect(outsideTheConfiguration(files)).toEqual([]);
  });

  it('finds the name changeable in the form of the configuration', () => {
    expect(outsideTheConfiguration(sourcesOf(SOURCES))).toEqual([]);
  });
});
