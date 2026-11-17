// ADR-voce-generale-con-la-zona-pericolosa (Bug 563): the emergency closing of every flow lives only in the page
// «Generale» of the settings, in its zone at the bottom, and the entry «Generale» opens the settings in the menu; the
// page of every day, the list of the flows, no longer offers it.
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

const GENERAL_SETTINGS = 'app/routes/app/general-settings.tsx';
const LAYOUT = 'components/layouts/dashboard-layout.tsx';
const EVERY_FLOW = /<EmergencyClosingCommand\s+scope=\{\{\s*kind:\s*'all'\s*\}\}/;
const IN_THE_ZONE =
  /<DangerZone>\s*<EmergencyClosingCommand\s+scope=\{\{\s*kind:\s*'all'\s*\}\}\s*\/>\s*<\/DangerZone>/;
const GENERAL_ENTRY = /name:\s*'Generale',\s*to:\s*paths\.generalSettings\.getHref\(\)/;

const outsideGeneralSettings = (files: readonly SourceFile[]): string[] =>
  files
    .filter((file) => file.path !== GENERAL_SETTINGS && EVERY_FLOW.test(file.source))
    .map((file) => `${file.path}: chiusura di emergenza di tutti i flussi fuori da «Generale»`);

const missingFromTheZone = (files: readonly SourceFile[]): string[] => {
  const page = files.find((file) => file.path === GENERAL_SETTINGS);
  return page !== undefined && IN_THE_ZONE.test(page.source)
    ? []
    : [
        `${GENERAL_SETTINGS}: manca la chiusura di emergenza di tutti i flussi nella zona di emergenza`,
      ];
};

const missingFromTheMenu = (files: readonly SourceFile[]): string[] => {
  const layout = files.find((file) => file.path === LAYOUT);
  return layout !== undefined && GENERAL_ENTRY.test(layout.source)
    ? []
    : [`${LAYOUT}: manca la voce «Generale» delle impostazioni`];
};

/** Where the emergency closing of every flow breaks the decision. */
const misplacedClosingsOfEveryFlow = (files: readonly SourceFile[]): string[] => [
  ...outsideGeneralSettings(files),
  ...missingFromTheZone(files),
  ...missingFromTheMenu(files),
];

const file = (path: string, source: string): SourceFile => ({ path, source });

const HOME = 'app/routes/app/home.tsx';

const conforming = (): SourceFile[] => [
  file(
    GENERAL_SETTINGS,
    "<DangerZone>\n  <EmergencyClosingCommand scope={{ kind: 'all' }} />\n</DangerZone>",
  ),
  file(LAYOUT, "{ name: 'Generale', to: paths.generalSettings.getHref(), area: [] }"),
  file(HOME, '<FlowsList />'),
  file('app/routes/app/accounts.tsx', "<EmergencyClosingCommand scope={{ kind: 'account' }} />"),
];

const replaced = (files: readonly SourceFile[], path: string, source: string): SourceFile[] =>
  files.map((each) => (each.path === path ? file(path, source) : each));

describe('ADR-voce-generale-con-la-zona-pericolosa: the emergency closing of every flow in «Generale»', () => {
  it('is red when the list of the flows offers the emergency closing of every flow', () => {
    const files = replaced(
      conforming(),
      HOME,
      "<DangerZone><EmergencyClosingCommand scope={{ kind: 'all' }} /></DangerZone>",
    );

    expect(misplacedClosingsOfEveryFlow(files)).toEqual([
      `${HOME}: chiusura di emergenza di tutti i flussi fuori da «Generale»`,
    ]);
  });

  it('is red when «Generale» offers the command outside the zone of emergency', () => {
    const files = replaced(
      conforming(),
      GENERAL_SETTINGS,
      "<EmergencyClosingCommand scope={{ kind: 'all' }} />",
    );

    expect(misplacedClosingsOfEveryFlow(files)).toEqual([
      `${GENERAL_SETTINGS}: manca la chiusura di emergenza di tutti i flussi nella zona di emergenza`,
    ]);
  });

  it('is red when the menu has no entry «Generale»', () => {
    const files = conforming().filter((each) => each.path !== LAYOUT);

    expect(misplacedClosingsOfEveryFlow(files)).toEqual([
      `${LAYOUT}: manca la voce «Generale» delle impostazioni`,
    ]);
  });

  it('is silent when only «Generale» offers it, in its zone, reached from the menu', () => {
    expect(misplacedClosingsOfEveryFlow(conforming())).toEqual([]);
  });

  it('finds the emergency closing of every flow only in «Generale» of the dashboard', () => {
    expect(misplacedClosingsOfEveryFlow(sourcesOf(SOURCES))).toEqual([]);
  });
});
