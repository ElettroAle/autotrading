// ADR-posizione-evidenziata-dall-indirizzo (R3.5.6): the position the address of a notification points at stands out
// in the tabs Posizioni and Posizioni chiuse through the one prop of the shared table, never through a highlight of
// their own; the closed positions read the instant of the closing and lead to the history when the row is elsewhere.
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
    .filter((path) => !path.startsWith('testing/') && !path.endsWith('.d.ts'))
    .map((path) => ({ path, source: readFileSync(join(directory, path), 'utf8') }));

const DATA_TABLE = 'components/ui/data-table.tsx';
const OPEN_POSITIONS = 'features/flow-positions/components/open-positions.tsx';
const CLOSED_POSITIONS = 'features/flow-positions/components/closed-positions.tsx';
const HIGHLIGHT_TEXT = /'Dalla notifica'/;
const HIGHLIGHTED_ROW = /\bhighlightedRow=\{/;
const CLOSED_AT = /'closed_at'/;
const HISTORY = /\bpaths\.history\.getHref\(\)/;

const highlightOutsideTheTable = (files: readonly SourceFile[]): string[] =>
  files
    .filter((file) => file.path !== DATA_TABLE && HIGHLIGHT_TEXT.test(file.source))
    .map((file) => `${file.path}: evidenza propria fuori da DataTable`);

const tabProblems = (
  files: readonly SourceFile[],
  path: string,
  rules: readonly [RegExp, string][],
) => {
  const tab = files.find((file) => file.path === path);
  if (tab === undefined) {
    return [`${path}: mancante`];
  }
  return rules.filter(([rule]) => !rule.test(tab.source)).map(([, reason]) => `${path}: ${reason}`);
};

/** Each file that breaks the decision, with the reason. */
const misplacedHighlight = (files: readonly SourceFile[]): string[] => [
  ...highlightOutsideTheTable(files),
  ...(HIGHLIGHT_TEXT.test(files.find((file) => file.path === DATA_TABLE)?.source ?? '')
    ? []
    : [`${DATA_TABLE}: la riga evidenziata non lo dice con un testo`]),
  ...tabProblems(files, OPEN_POSITIONS, [[HIGHLIGHTED_ROW, 'non evidenzia la riga']]),
  ...tabProblems(files, CLOSED_POSITIONS, [
    [HIGHLIGHTED_ROW, 'non evidenzia la riga'],
    [CLOSED_AT, "non legge l'istante della chiusura"],
    [HISTORY, 'non porta allo Storico'],
  ]),
];

const file = (path: string, source: string): SourceFile => ({ path, source });

const conforming = (): SourceFile[] => [
  file(DATA_TABLE, "const HIGHLIGHT_TEXT = 'Dalla notifica';"),
  file(OPEN_POSITIONS, '<DataTable highlightedRow={(position) => position.asset === asset} />'),
  file(
    CLOSED_POSITIONS,
    "search.get('closed_at'); paths.history.getHref(); <DataTable highlightedRow={(position) => isNotified(position)} />",
  ),
];

const replaced = (files: readonly SourceFile[], path: string, source: string): SourceFile[] =>
  files.map((each) => (each.path === path ? file(path, source) : each));

describe('ADR-posizione-evidenziata-dall-indirizzo: the position of the address stands out through DataTable', () => {
  it('is red when a tab highlights a row on its own', () => {
    const files = replaced(
      conforming(),
      OPEN_POSITIONS,
      "<tr aria-current><td>BTC <span>{'Dalla notifica'}</span></td></tr>",
    );

    expect(misplacedHighlight(files)).toEqual([
      `${OPEN_POSITIONS}: evidenza propria fuori da DataTable`,
      `${OPEN_POSITIONS}: non evidenzia la riga`,
    ]);
  });

  it('is red when the table marks the row by colour alone', () => {
    const files = replaced(conforming(), DATA_TABLE, "const HIGHLIGHTED = 'bg-amber-50';");

    expect(misplacedHighlight(files)).toEqual([
      `${DATA_TABLE}: la riga evidenziata non lo dice con un testo`,
    ]);
  });

  it('is red when the closed positions ignore the instant and the history', () => {
    const files = replaced(
      conforming(),
      CLOSED_POSITIONS,
      '<DataTable highlightedRow={(position) => position.asset === asset} />',
    );

    expect(misplacedHighlight(files)).toEqual([
      `${CLOSED_POSITIONS}: non legge l'istante della chiusura`,
      `${CLOSED_POSITIONS}: non porta allo Storico`,
    ]);
  });

  it('is red when a tab is missing', () => {
    const files = conforming().filter((each) => each.path !== CLOSED_POSITIONS);

    expect(misplacedHighlight(files)).toEqual([`${CLOSED_POSITIONS}: mancante`]);
  });

  it('is silent when both tabs highlight through DataTable', () => {
    expect(misplacedHighlight(conforming())).toEqual([]);
  });

  it('finds the highlight of the dashboard only in DataTable, used by both tabs', () => {
    expect(misplacedHighlight(sourcesOf(SOURCES))).toEqual([]);
  });
});
