// ADR opzioni-della-memoria-nella-dashboard (R5.3.7): in the section «Memoria» of the form, after «Tutte le decisioni»,
// the switches «Riepilogo per asset e direzione» and «Altri asset del flusso», each with its help and enabled only with
// the memory on; the memory shown puts the summary lines of an asset and of the other assets before its table, with the
// text of the API: no code of the dashboard writes a summary line of its own.
import { readdirSync, readFileSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

const SOURCES = fileURLToPath(new URL('../src', import.meta.url));
const FIELDS = 'features/flow-editor/components/memory-fields.tsx';
const TABLE = 'components/ui/flow-memory-table.tsx';

type SourceFile = { readonly path: string; readonly source: string };

const isTest = (path: string): boolean => /\.test\.tsx?$/.test(path) || path.startsWith('testing/');

const sourcesOf = (directory: string): SourceFile[] =>
  readdirSync(directory, { recursive: true, encoding: 'utf8' })
    .map((path) => relative(directory, join(directory, path)).split(sep).join('/'))
    .filter((path) => /\.tsx?$/.test(path) && !path.endsWith('.d.ts') && !isTest(path))
    .map((path) => ({ path, source: readFileSync(join(directory, path), 'utf8') }));

// The words of the line the API writes: a dashboard that writes them computes the summary itself.
const LINE_WORDS = /chiuse, .*vinte, .*perse/;

// The tag of the option with the label, up to its end.
const optionOf = (source: string, label: string): string =>
  source
    .split('<MemoryOption')
    .slice(1)
    .map((tag) => tag.slice(0, tag.indexOf('/>')))
    .find((tag) => tag.includes(`label="${label}"`)) ?? '';

const FIELD_RULES: readonly {
  readonly breach: string;
  readonly holds: (source: string) => boolean;
}[] = [
  {
    breach: 'le opzioni non seguono «Tutte le decisioni»',
    holds: (source) =>
      source.indexOf('Tutte le decisioni') >= 0 &&
      source.indexOf('Tutte le decisioni') < source.indexOf('Riepilogo per asset e direzione') &&
      source.indexOf('Riepilogo per asset e direzione') < source.indexOf('Altri asset del flusso'),
  },
  {
    breach: 'un’opzione non ha la riga di aiuto o non dipende dalla memoria attiva',
    holds: (source) =>
      ['Riepilogo per asset e direzione', 'Altri asset del flusso'].every((label) => {
        const option = optionOf(source, label);
        return /hint="[^"]+"/.test(option) && option.includes('disabled={!active}');
      }),
  },
];

const fieldBreachesOf = (source: string): string[] =>
  FIELD_RULES.filter((rule) => !rule.holds(source)).map((rule) => rule.breach);

const tableBreachesOf = (source: string): string[] => {
  const table = source.indexOf('<DataTable');
  const summary = source.indexOf('lines={summary}');
  const others = source.indexOf('lines={otherAssets}');
  return summary >= 0 && others >= 0 && summary < table && others < table
    ? []
    : ['le righe di riepilogo non precedono la tabella delle decisioni'];
};

const lineWriters = (files: readonly SourceFile[]): string[] =>
  files.filter((file) => LINE_WORDS.test(file.source)).map((file) => file.path);

const CONFORMING_FIELDS = `
  <label><input type="checkbox" {...register('memory.all_decisions')} disabled={!active} />Tutte le decisioni</label>
  <MemoryOption name="memory.summary" label="Riepilogo per asset e direzione" hint="una riga per direzione" disabled={!active} />
  <MemoryOption name="memory.other_assets" label="Altri asset del flusso" hint="le righe degli altri asset" disabled={!active} />`;
const CONFORMING_TABLE = `
  <SummaryLines label={label} lines={summary} />
  <SummaryLines label="Altri asset del flusso" lines={otherAssets} />
  <DataTable rows={entries} />`;

describe('ADR opzioni-della-memoria-nella-dashboard: the summary and the other assets of the memory', () => {
  it('is red when the options come before «Tutte le decisioni»', () => {
    const before = CONFORMING_FIELDS.split('\n').reverse().join('\n');

    expect(fieldBreachesOf(before)).toContain('le opzioni non seguono «Tutte le decisioni»');
  });

  it('is red when an option has no help or stays enabled with the memory off', () => {
    expect(
      fieldBreachesOf(CONFORMING_FIELDS.replace(' hint="una riga per direzione"', '')),
    ).toEqual(['un’opzione non ha la riga di aiuto o non dipende dalla memoria attiva']);
    expect(
      fieldBreachesOf(
        CONFORMING_FIELDS.replace(
          'hint="le righe degli altri asset" disabled={!active}',
          'hint="le righe degli altri asset"',
        ),
      ),
    ).toEqual(['un’opzione non ha la riga di aiuto o non dipende dalla memoria attiva']);
  });

  it('is red when the summary lines follow the table', () => {
    expect(
      tableBreachesOf('<DataTable rows={entries} />\n<SummaryLines lines={summary} />'),
    ).toEqual(['le righe di riepilogo non precedono la tabella delle decisioni']);
  });

  it('is red when a source writes the words of the summary line itself', () => {
    expect(
      lineWriters([{ path: 'x.tsx', source: '`${closed} chiuse, ${won} vinte, ${lost} perse`' }]),
    ).toEqual(['x.tsx']);
  });

  it('is silent on the conforming form and table', () => {
    expect(fieldBreachesOf(CONFORMING_FIELDS)).toEqual([]);
    expect(tableBreachesOf(CONFORMING_TABLE)).toEqual([]);
    expect(lineWriters([{ path: 'y.tsx', source: '<li>{line}</li>' }])).toEqual([]);
  });

  it('finds the options in the form, the lines before the table and no summary written by the dashboard', () => {
    const files = sourcesOf(SOURCES);
    const sourceOf = (path: string): string =>
      files.find((each) => each.path === path)?.source ?? '';

    expect(fieldBreachesOf(sourceOf(FIELDS))).toEqual([]);
    expect(tableBreachesOf(sourceOf(TABLE))).toEqual([]);
    expect(lineWriters(files)).toEqual([]);
  });
});
