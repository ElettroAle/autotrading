// ADR-stato-della-riconciliazione-nella-dashboard (R3.3.2): the reconciliation of an account lives in the feature
// accounts, built on the shared components, and the dashboard decides nothing of it: whether an account is aligned and
// why the openings of a flow are suspended are the API's.
import { readdirSync, readFileSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

const SOURCES = fileURLToPath(new URL('../src', import.meta.url));

type SourceFile = { readonly path: string; readonly source: string };

const isTest = (path: string): boolean => /\.test\.tsx?$/.test(path);

// The fakes of the API speak its words on purpose: they are not the dashboard.
const isFake = (path: string): boolean => path.startsWith('testing/');

const sourcesOf = (directory: string): SourceFile[] =>
  readdirSync(directory, { recursive: true, encoding: 'utf8' })
    .filter((path) => /\.tsx?$/.test(path) && !isTest(path))
    .map((path) => relative(directory, join(directory, path)).split(sep).join('/'))
    .filter((path) => !isFake(path) && !path.endsWith('.d.ts'))
    .map((path) => ({ path, source: readFileSync(join(directory, path), 'utf8') }));

const RECONCILIATION_ENDPOINT =
  /'\/accounts\/\{account_id\}\/(reconciliation|deviation-threshold)[^']*'/g;
const CONFIRMATION_ENDPOINT = "'/accounts/{account_id}/reconciliation/confirmation'";
const ACCOUNTS_API = 'features/accounts/api/';
// ADR-pagina-avvisi-nella-dashboard: the detail of an alarm confirms the balance with the command of the API.
const ALERTS_API = 'features/alerts/api/';

const isAdmitted = (path: string, endpoints: readonly string[]): boolean =>
  path.startsWith(ACCOUNTS_API) ||
  (path.startsWith(ALERTS_API) &&
    endpoints.every((endpoint) => endpoint === CONFIRMATION_ENDPOINT));

/**
 * The files that call the reconciliation of the API outside the API of the feature accounts; the API of the alerts
 * may only confirm the balance.
 */
const callsOutsideAccounts = (files: readonly SourceFile[]): string[] =>
  files
    .map((file) => ({
      path: file.path,
      endpoints: file.source.match(RECONCILIATION_ENDPOINT) ?? [],
    }))
    .filter(({ path, endpoints }) => endpoints.length > 0 && !isAdmitted(path, endpoints))
    .map(({ path }) => path);

// The reason of the suspension the API gives, as the dashboard would rewrite it.
const DECIDED_BY_THE_API = /allarme di riconciliazione sul conto/;

/** The files that write a reason the API gives, as if the dashboard decided it. */
const reasonsWrittenByTheDashboard = (files: readonly SourceFile[]): string[] =>
  files.filter((file) => DECIDED_BY_THE_API.test(file.source)).map((file) => file.path);

/**
 * The shared components each view of the reconciliation is built on, as the owner decided (16/11/2026); the alarms of
 * an account are listed with the alerts (ADR-pagina-avvisi-nella-dashboard).
 */
const SHARED_COMPONENTS: Readonly<Record<string, readonly string[]>> = {
  'features/accounts/components/reconciliation-status.tsx': [
    '@/components/ui/confirmation-dialog',
    '@/components/ui/details-list',
  ],
  'features/alerts/components/alerts-list.tsx': ['@/components/ui/data-table'],
  'features/accounts/components/deviation-threshold-form.tsx': ['@/components/ui/form/input-field'],
};

/** Each view of the reconciliation that is missing, or that does not import a shared component it is built on. */
const viewsWithoutSharedComponents = (files: readonly SourceFile[]): string[] =>
  Object.entries(SHARED_COMPONENTS).flatMap(([path, components]) => {
    const file = files.find((candidate) => candidate.path === path);
    if (file === undefined) {
      return [`${path}: mancante`];
    }
    return components
      .filter((component) => !file.source.includes(`from '${component}'`))
      .map((component) => `${path}: non usa ${component}`);
  });

const file = (path: string, source: string): SourceFile => ({ path, source });

const conformingViews = (): SourceFile[] => [
  file(
    'features/accounts/components/reconciliation-status.tsx',
    "import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';\n" +
      "import { DETAILS_GRID } from '@/components/ui/details-list';\n",
  ),
  file(
    'features/alerts/components/alerts-list.tsx',
    "import { DataTable } from '@/components/ui/data-table';\n",
  ),
  file(
    'features/accounts/components/deviation-threshold-form.tsx',
    "import { InputField } from '@/components/ui/form/input-field';\n",
  ),
];

describe('ADR-stato-della-riconciliazione-nella-dashboard: the reconciliation in the feature accounts', () => {
  it('is red when another feature calls the reconciliation of the API', () => {
    const files = [
      file(
        'features/accounts/api/get-account-reconciliation.ts',
        "api.GET('/accounts/{account_id}/reconciliation')",
      ),
      file(
        'features/flows/api/get-alarms.ts',
        "api.GET('/accounts/{account_id}/reconciliation/alarms')",
      ),
      file(
        'features/flows/api/set-threshold.ts',
        "api.PUT('/accounts/{account_id}/deviation-threshold')",
      ),
      file(
        'features/alerts/api/get-alarms.ts',
        "api.GET('/accounts/{account_id}/reconciliation/alarms')",
      ),
    ];

    expect(callsOutsideAccounts(files)).toEqual([
      'features/flows/api/get-alarms.ts',
      'features/flows/api/set-threshold.ts',
      'features/alerts/api/get-alarms.ts',
    ]);
  });

  it('is silent when only the API of the feature accounts calls it', () => {
    const files = [
      file(
        'features/accounts/api/confirm-reconciliation.ts',
        "api.POST('/accounts/{account_id}/reconciliation/confirmation')",
      ),
      file('features/accounts/api/get-account-state.ts', "api.GET('/accounts/{account_id}/state')"),
      file(
        'features/alerts/api/run-alert-command.ts',
        "api.POST('/accounts/{account_id}/reconciliation/confirmation')",
      ),
    ];

    expect(callsOutsideAccounts(files)).toEqual([]);
  });

  it('finds no call of the reconciliation outside the feature accounts', () => {
    expect(callsOutsideAccounts(sourcesOf(SOURCES))).toEqual([]);
  });
});

describe('ADR-stato-della-riconciliazione-nella-dashboard: the API decides, the dashboard shows', () => {
  it('is red when the dashboard writes the reason of the suspension itself', () => {
    const files = [
      file(
        'features/flows/components/notice.tsx',
        '`aperture sospese: allarme di riconciliazione sul conto ${name}`',
      ),
      file('features/flows/components/head.tsx', '`aperture sospese: ${reason}`'),
    ];

    expect(reasonsWrittenByTheDashboard(files)).toEqual(['features/flows/components/notice.tsx']);
  });

  it('finds no reason of the API written by the dashboard', () => {
    expect(reasonsWrittenByTheDashboard(sourcesOf(SOURCES))).toEqual([]);
  });
});

describe('ADR-stato-della-riconciliazione-nella-dashboard: built on the shared components', () => {
  it('is red when a view of the reconciliation builds its own table, list or window', () => {
    const [status, , form] = conformingViews();
    const files = [
      status ?? file('', ''),
      file('features/alerts/components/alerts-list.tsx', '<table aria-label="Allarmi">'),
      form ?? file('', ''),
    ];

    expect(viewsWithoutSharedComponents(files)).toEqual([
      'features/alerts/components/alerts-list.tsx: non usa @/components/ui/data-table',
    ]);
  });

  it('is red when a view of the reconciliation is missing', () => {
    expect(viewsWithoutSharedComponents(conformingViews().slice(0, 2))).toEqual([
      'features/accounts/components/deviation-threshold-form.tsx: mancante',
    ]);
  });

  it('is silent when every view imports its shared components', () => {
    expect(viewsWithoutSharedComponents(conformingViews())).toEqual([]);
  });

  it('finds every view of the dashboard built on its shared components', () => {
    expect(viewsWithoutSharedComponents(sourcesOf(SOURCES))).toEqual([]);
  });
});
