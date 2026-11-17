// ADR-chiusura-di-emergenza-nella-dashboard (R3.2.3): one feature, emergency-closing, with one command for the three
// scopes, built on the shared confirmation; the pages of the flow, of the accounts and «Generale» compose it, and no
// other code calls the emergency closing of the API.
import { readdirSync, readFileSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

const SOURCES = fileURLToPath(new URL('../src', import.meta.url));

type SourceFile = { readonly path: string; readonly source: string };

const isTest = (path: string): boolean => /\.test\.tsx?$/.test(path);

// The fakes of the API answer its routes on purpose: they are not the dashboard.
const isFake = (path: string): boolean => path.startsWith('testing/');

const sourcesOf = (directory: string): SourceFile[] =>
  readdirSync(directory, { recursive: true, encoding: 'utf8' })
    .filter((path) => /\.tsx?$/.test(path) && !isTest(path))
    .map((path) => relative(directory, join(directory, path)).split(sep).join('/'))
    .filter((path) => !isFake(path) && !path.endsWith('.d.ts'))
    .map((path) => ({ path, source: readFileSync(join(directory, path), 'utf8') }));

const EMERGENCY_ENDPOINT = /'\/flows\/emergency-closings/;
const FEATURE_API = 'features/emergency-closing/api/';
const COMMAND = 'features/emergency-closing/components/emergency-closing-command.tsx';
const COMMAND_IMPORT = "from '@/features/emergency-closing/components/emergency-closing-command'";
const SHARED_CONFIRMATION = "from '@/components/ui/confirmation-dialog'";

/**
 * The pages that offer the emergency closing, one per scope; every flow from «Generale» of the settings (ADR
 * voce-generale-con-la-zona-pericolosa).
 */
const PAGES = [
  'app/routes/app/flow-settings.tsx',
  'app/routes/app/accounts.tsx',
  'app/routes/app/general-settings.tsx',
];

/** The files that call the emergency closing of the API outside the API of its feature. */
const callsOutsideTheFeature = (files: readonly SourceFile[]): string[] =>
  files
    .filter((file) => EMERGENCY_ENDPOINT.test(file.source))
    .filter((file) => !file.path.startsWith(FEATURE_API))
    .map((file) => file.path);

/** Each page that is missing or does not compose the one command; the command missing or without the confirmation. */
const pagesWithoutTheCommand = (files: readonly SourceFile[]): string[] => {
  const command = files.find((file) => file.path === COMMAND);
  const commandProblems =
    command === undefined
      ? [`${COMMAND}: mancante`]
      : command.source.includes(SHARED_CONFIRMATION)
        ? []
        : [`${COMMAND}: non usa la conferma condivisa`];
  const pageProblems = PAGES.filter(
    (page) => !(files.find((file) => file.path === page)?.source.includes(COMMAND_IMPORT) ?? false),
  ).map((page) => `${page}: non compone EmergencyClosingCommand`);
  return [...commandProblems, ...pageProblems];
};

const file = (path: string, source: string): SourceFile => ({ path, source });

const conforming = (): SourceFile[] => [
  file(COMMAND, `import { ConfirmationDialog } ${SHARED_CONFIRMATION};`),
  ...PAGES.map((page) => file(page, `import { EmergencyClosingCommand } ${COMMAND_IMPORT};`)),
];

describe('ADR-chiusura-di-emergenza-nella-dashboard: one feature calls the emergency closing', () => {
  it('is red when another feature calls the emergency closing of the API', () => {
    const files = [
      file(`${FEATURE_API}close-in-emergency.ts`, "api.POST('/flows/emergency-closings')"),
      file('features/accounts/api/close-account.ts', "api.POST('/flows/emergency-closings')"),
      file('features/flows/api/preview.ts', "api.GET('/flows/emergency-closings/preview')"),
    ];

    expect(callsOutsideTheFeature(files)).toEqual([
      'features/accounts/api/close-account.ts',
      'features/flows/api/preview.ts',
    ]);
  });

  it('is silent when only the API of the feature calls it', () => {
    const files = [
      file(
        `${FEATURE_API}get-emergency-closing-preview.ts`,
        "api.GET('/flows/emergency-closings/preview')",
      ),
      file(
        'features/flow-commands/api/cash-out-profits.ts',
        "api.POST('/flows/{flow_id}/cash-out')",
      ),
    ];

    expect(callsOutsideTheFeature(files)).toEqual([]);
  });

  it('finds no call of the emergency closing outside its feature', () => {
    expect(callsOutsideTheFeature(sourcesOf(SOURCES))).toEqual([]);
  });
});

describe('ADR-chiusura-di-emergenza-nella-dashboard: one command, composed by the three pages', () => {
  it('is red when a page builds its own command instead of composing the one', () => {
    const [command, flowPage, , homePage] = conforming();
    const files = [
      command ?? file('', ''),
      flowPage ?? file('', ''),
      file('app/routes/app/accounts.tsx', '<button>Chiusura di emergenza</button>'),
      homePage ?? file('', ''),
    ];

    expect(pagesWithoutTheCommand(files)).toEqual([
      'app/routes/app/accounts.tsx: non compone EmergencyClosingCommand',
    ]);
  });

  it('is red when the command builds its own confirmation', () => {
    const files = [file(COMMAND, '<div role="alertdialog">'), ...conforming().slice(1)];

    expect(pagesWithoutTheCommand(files)).toEqual([`${COMMAND}: non usa la conferma condivisa`]);
  });

  it('is red when the command is missing', () => {
    expect(pagesWithoutTheCommand(conforming().slice(1))).toEqual([`${COMMAND}: mancante`]);
  });

  it('is silent when the three pages compose the command built on the shared confirmation', () => {
    expect(pagesWithoutTheCommand(conforming())).toEqual([]);
  });

  it('finds the command on the three pages of the dashboard', () => {
    expect(pagesWithoutTheCommand(sourcesOf(SOURCES))).toEqual([]);
  });
});
