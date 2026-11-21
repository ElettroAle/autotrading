// ADR-pagina-del-flusso-archiviato-in-sola-lettura (Bug 690): the page of the flow reads the flow alone, so the address
// of an archived flow opens it in read only; the list of the flows, which leaves the archived out, is never where the
// page looks for its flow.
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

const SOURCES = fileURLToPath(new URL('../src', import.meta.url));

/** What the page of the flow shows of the flow it reads: its head, its overview and its title. */
const PAGE_OF_THE_FLOW = [
  'features/flows/components/flow-view.tsx',
  'features/flows/components/flow-opening.tsx',
  'features/flows/hooks/use-flow-title.ts',
] as const;

type SourceFile = { readonly path: string; readonly source: string };

const READS_THE_LIST = /\buseFlows\s*\(/;
const READS_THE_FLOW = /\buseFlow\s*\(/;

/** Each file of the page of the flow that looks for its flow in the list, or does not read it alone. */
const pageReadingsOfTheList = (files: readonly SourceFile[]): string[] =>
  files.flatMap((file) => [
    ...(READS_THE_LIST.test(file.source) ? [`${file.path}: cerca il flusso nell'elenco`] : []),
    ...(READS_THE_FLOW.test(file.source) ? [] : [`${file.path}: non legge il flusso da solo`]),
  ]);

const pageFiles = (): SourceFile[] =>
  PAGE_OF_THE_FLOW.map((path) => ({ path, source: readFileSync(join(SOURCES, path), 'utf8') }));

const view = (source: string): SourceFile[] => [
  { path: 'features/flows/components/flow-view.tsx', source },
];

describe('ADR-pagina-del-flusso-archiviato-in-sola-lettura: the page reads the flow alone', () => {
  it('is red when the page looks for its flow in the list of the flows', () => {
    const source =
      'const flow = useFlows().data?.find((candidate) => candidate.id === flowId);\nuseFlow(flowId);';

    expect(pageReadingsOfTheList(view(source))).toEqual([
      "features/flows/components/flow-view.tsx: cerca il flusso nell'elenco",
    ]);
  });

  it('is red when the page does not read the flow alone', () => {
    expect(pageReadingsOfTheList(view('const flow = undefined;'))).toEqual([
      'features/flows/components/flow-view.tsx: non legge il flusso da solo',
    ]);
  });

  it('is silent when the page reads the flow alone', () => {
    expect(pageReadingsOfTheList(view('const read = useFlow(flowId);'))).toEqual([]);
  });

  it('finds every file of the page of the flow reading the flow alone', () => {
    expect(pageReadingsOfTheList(pageFiles())).toEqual([]);
  });
});
