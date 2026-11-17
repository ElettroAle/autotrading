// ADR-impostazioni-del-flusso-dall-ingranaggio (Bug 560): the page of the flow holds reading and the commands of every
// day; the emergency closing of the flow and Archivia stand only in the settings of the flow, in its zone of danger.
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

const SETTINGS_PAGE = 'app/routes/app/flow-settings.tsx';
const ARCHIVE_COMMAND = 'features/flow-commands/components/archive-flow-command.tsx';

// The emergency closing of one flow, Archivia composed by a page, and the confirmation of the archiving shown.
const FLOW_EMERGENCY = /scope=\{\{\s*kind: 'flow'/;
const ARCHIVE_IMPORT = /from '@\/features\/flow-commands\/components\/archive-flow-command'/;
const ARCHIVE_CONFIRMATION = /<ArchiveConfirmation\b/;

/** Every file that offers the emergency closing of a flow or Archivia outside the settings of the flow. */
const outsideTheSettings = (files: readonly SourceFile[]): string[] => [
  ...files
    .filter((file) => FLOW_EMERGENCY.test(file.source) && file.path !== SETTINGS_PAGE)
    .map((file) => `${file.path}: chiusura di emergenza del flusso`),
  ...files
    .filter((file) => ARCHIVE_IMPORT.test(file.source) && file.path !== SETTINGS_PAGE)
    .map((file) => `${file.path}: Archivia`),
  ...files
    .filter((file) => ARCHIVE_CONFIRMATION.test(file.source) && file.path !== ARCHIVE_COMMAND)
    .map((file) => `${file.path}: conferma dell'archiviazione`),
];

const file = (path: string, source: string): SourceFile => ({ path, source });

const conforming = (): SourceFile[] => [
  file(
    SETTINGS_PAGE,
    `import { ArchiveFlowCommand } from '@/features/flow-commands/components/archive-flow-command';
     <EmergencyClosingCommand scope={{ kind: 'flow', flowId, flowName }} />`,
  ),
  file(ARCHIVE_COMMAND, '<ArchiveConfirmation pending={pending} />'),
  file(
    'app/routes/app/general-settings.tsx',
    "<EmergencyClosingCommand scope={{ kind: 'all' }} />",
  ),
];

describe('ADR-impostazioni-del-flusso-dall-ingranaggio: the commands of danger of a flow are in its settings', () => {
  it('is red when the page of the flow offers the emergency closing of the flow', () => {
    const files = [
      ...conforming(),
      file('app/routes/app/flow.tsx', "<EmergencyClosingCommand scope={{ kind: 'flow' }} />"),
    ];

    expect(outsideTheSettings(files)).toEqual([
      'app/routes/app/flow.tsx: chiusura di emergenza del flusso',
    ]);
  });

  it('is red when another page composes Archivia', () => {
    const files = [
      ...conforming(),
      file(
        'app/routes/app/flow.tsx',
        "import { ArchiveFlowCommand } from '@/features/flow-commands/components/archive-flow-command';",
      ),
    ];

    expect(outsideTheSettings(files)).toEqual(['app/routes/app/flow.tsx: Archivia']);
  });

  it('is red when the commands of every day archive the flow on their own', () => {
    const files = [
      ...conforming(),
      file(
        'features/flow-commands/components/flow-commands.tsx',
        '<ArchiveConfirmation onConfirm={archive} />',
      ),
    ];

    expect(outsideTheSettings(files)).toEqual([
      "features/flow-commands/components/flow-commands.tsx: conferma dell'archiviazione",
    ]);
  });

  it('is silent when only the settings of the flow offer them', () => {
    expect(outsideTheSettings(conforming())).toEqual([]);
  });

  it('finds the emergency closing of the flow and Archivia only in the settings of the flow', () => {
    expect(outsideTheSettings(sourcesOf(SOURCES))).toEqual([]);
  });
});
