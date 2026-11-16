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

const RECONCILIATION_ENDPOINT = /'\/accounts\/\{account_id\}\/(reconciliation|deviation-threshold)/;
const ACCOUNTS_API = 'features/accounts/api/';

/** The files that call the reconciliation of the API outside the API of the feature accounts. */
const callsOutsideAccounts = (files: readonly SourceFile[]): string[] =>
  files
    .filter((file) => RECONCILIATION_ENDPOINT.test(file.source))
    .filter((file) => !file.path.startsWith(ACCOUNTS_API))
    .map((file) => file.path);

// The reason of the suspension the API gives, as the dashboard would rewrite it.
const DECIDED_BY_THE_API = /allarme di riconciliazione sul conto/;

/** The files that write a reason the API gives, as if the dashboard decided it. */
const reasonsWrittenByTheDashboard = (files: readonly SourceFile[]): string[] =>
  files.filter((file) => DECIDED_BY_THE_API.test(file.source)).map((file) => file.path);

/** The shared components each view of the reconciliation is built on, as the owner decided (16/11/2026). */
const SHARED_COMPONENTS: Readonly<Record<string, readonly string[]>> = {
  'features/accounts/components/reconciliation-status.tsx': [
    '@/components/ui/confirmation-dialog',
    '@/components/ui/details-list',
  ],
  'features/accounts/components/reconciliation-alarms.tsx': ['@/components/ui/data-table'],
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
    'features/accounts/components/reconciliation-alarms.tsx',
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
    ];

    expect(callsOutsideAccounts(files)).toEqual([
      'features/flows/api/get-alarms.ts',
      'features/flows/api/set-threshold.ts',
    ]);
  });

  it('is silent when only the API of the feature accounts calls it', () => {
    const files = [
      file(
        'features/accounts/api/confirm-reconciliation.ts',
        "api.POST('/accounts/{account_id}/reconciliation/confirmation')",
      ),
      file('features/accounts/api/get-account-state.ts', "api.GET('/accounts/{account_id}/state')"),
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
      file(
        'features/accounts/components/reconciliation-alarms.tsx',
        '<table aria-label="Allarmi">',
      ),
      form ?? file('', ''),
    ];

    expect(viewsWithoutSharedComponents(files)).toEqual([
      'features/accounts/components/reconciliation-alarms.tsx: non usa @/components/ui/data-table',
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
