// ADR-pagina-avvisi-nella-dashboard (R6.2.3): the alerts live in the feature alerts, built on the shared table, filters
// and confirmation; the menu shows the number of the open alerts the API counts; the alarms of an account lead to its
// alerts; the scenarios of F6.2 run on the dashboard.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

const DASHBOARD = fileURLToPath(new URL('..', import.meta.url));

type SourceFile = { readonly path: string; readonly source: string };

const read = (path: string): SourceFile => ({
  path,
  source: readFileSync(`${DASHBOARD}${path}`, 'utf8'),
});

const file = (path: string, source: string): SourceFile => ({ path, source });

/** The shared components each view of the alerts is built on. */
const SHARED_COMPONENTS: Readonly<Record<string, readonly string[]>> = {
  'src/features/alerts/components/alerts-list.tsx': [
    '@/components/ui/data-table',
    '@/hooks/use-table-filters',
  ],
  'src/features/alerts/components/alert-detail.tsx': [
    '@/components/ui/confirmation-dialog',
    '@/components/ui/command-button',
  ],
  'src/features/alerts/components/alert-parts.tsx': ['@/components/ui/icons/icon'],
};

const viewsWithoutSharedComponents = (files: readonly SourceFile[]): string[] =>
  Object.entries(SHARED_COMPONENTS).flatMap(([path, components]) => {
    const view = files.find((candidate) => candidate.path === path);
    if (view === undefined) {
      return [`${path}: mancante`];
    }
    return components
      .filter((component) => !view.source.includes(`from '${component}'`))
      .map((component) => `${path}: non usa ${component}`);
  });

const LAYOUT = 'src/components/layouts/dashboard-layout.tsx';
const OPEN_ALERTS_COUNT = 'src/hooks/use-open-alerts-count.ts';
const ACCOUNT_ALARMS = 'src/app/routes/app/account-alarms.tsx';
const PLAYWRIGHT = 'playwright.config.ts';

/** What keeps the menu from showing the number of the open alerts as the API counts them. */
const menuViolations = (layout: SourceFile, count: SourceFile): string[] => [
  ...(layout.source.includes("name: 'Avvisi'") ? [] : ['nessuna voce Avvisi nel menu']),
  ...(layout.source.includes("from '@/hooks/use-open-alerts-count'")
    ? []
    : ['il menu non legge il numero degli aperti']),
  ...(count.source.includes("'/alerts/summary'") ? [] : ['il numero non viene da /alerts/summary']),
  ...(count.source.includes('pageDataQuery(') ? [] : ['il numero non si rilegge con la pagina']),
];

/** What keeps the address of the alarms of an account from leading to its alerts in every state. */
const redirectViolations = (route: SourceFile): string[] => [
  ...(route.source.includes('<Navigate replace') ? [] : ['non reindirizza']),
  ...(route.source.includes("state: 'all'") && route.source.includes('resource_id: accountId')
    ? []
    : ['non filtra gli avvisi del conto con tutti gli stati']),
];

// The alerts of F6.2 have their scenarios in the files of the system dashboard (ADR
// scenari-per-sistema-sotto-la-user-story).
const DASHBOARD_FEATURES = "'../specs/**/dashboard/*.feature'";

describe('ADR-pagina-avvisi-nella-dashboard: the views of the alerts on the shared components', () => {
  it('is red when a view builds its own table or window', () => {
    const files = [
      file('src/features/alerts/components/alerts-list.tsx', '<table aria-label="Avvisi">'),
      file(
        'src/features/alerts/components/alert-detail.tsx',
        'import { CommandButton } from \'@/components/ui/command-button\';\n<div role="dialog">',
      ),
    ];

    expect(viewsWithoutSharedComponents(files)).toEqual([
      'src/features/alerts/components/alerts-list.tsx: non usa @/components/ui/data-table',
      'src/features/alerts/components/alerts-list.tsx: non usa @/hooks/use-table-filters',
      'src/features/alerts/components/alert-detail.tsx: non usa @/components/ui/confirmation-dialog',
      'src/features/alerts/components/alert-parts.tsx: mancante',
    ]);
  });

  it('finds every view of the alerts built on its shared components', () => {
    expect(viewsWithoutSharedComponents(Object.keys(SHARED_COMPONENTS).map(read))).toEqual([]);
  });
});

describe('ADR-pagina-avvisi-nella-dashboard: the number of the open alerts in the menu', () => {
  it('is red when the menu has no entry or counts by itself', () => {
    const layout = file(LAYOUT, "{ name: 'Storico' }");
    const count = file(OPEN_ALERTS_COUNT, "useQuery({ queryKey: ['alerts'] })");

    expect(menuViolations(layout, count)).toEqual([
      'nessuna voce Avvisi nel menu',
      'il menu non legge il numero degli aperti',
      'il numero non viene da /alerts/summary',
      'il numero non si rilegge con la pagina',
    ]);
  });

  it('shows the number the API counts, reread with the page', () => {
    expect(menuViolations(read(LAYOUT), read(OPEN_ALERTS_COUNT))).toEqual([]);
  });
});

describe('ADR-pagina-avvisi-nella-dashboard: the alarms of an account are its alerts', () => {
  it('is red when the address of the alarms keeps a page of its own', () => {
    expect(
      redirectViolations(file(ACCOUNT_ALARMS, '<ReconciliationAlarms accountId={accountId} />')),
    ).toEqual(['non reindirizza', 'non filtra gli avvisi del conto con tutti gli stati']);
  });

  it('leads the address of the alarms to the alerts of the account in every state', () => {
    expect(redirectViolations(read(ACCOUNT_ALARMS))).toEqual([]);
  });

  it('runs the scenarios of the alerts on the dashboard', () => {
    expect(read(PLAYWRIGHT).source).toContain(DASHBOARD_FEATURES);
  });
});
