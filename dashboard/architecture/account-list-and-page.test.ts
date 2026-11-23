// ADR-elenco-dei-conti-e-pagina-del-conto (Bug 616): the page of the accounts is a compact list, each element with only
// name, network, state of the reconciliation, balance and free capital and its actions in a menu; the rest of the
// account is on its page, with the four tabs of ViewTabs, the removal in the DangerZone and «Indietro» towards the
// accounts.
import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

const SOURCES = fileURLToPath(new URL('../src', import.meta.url));

type SourceFile = { readonly path: string; readonly source: string };

const ITEM = 'features/accounts/components/account-item.tsx';
const ACTIONS = 'features/accounts/components/account-actions.tsx';
const TABS = 'features/accounts/components/account-tabs.tsx';
const SETTINGS = 'features/accounts/components/account-settings.tsx';
const PAGE = 'app/routes/app/account.tsx';
const LONG_BOX = 'features/accounts/components/account-card.tsx';

const PAGE_FILES = [ITEM, ACTIONS, TABS, SETTINGS, PAGE] as const;

const read = (paths: readonly string[]): SourceFile[] =>
  paths
    .filter((path) => existsSync(`${SOURCES}/${path}`))
    .map((path) => ({ path, source: readFileSync(`${SOURCES}/${path}`, 'utf8') }));

/** The modules a file imports, as written after «from». */
const importsOf = (source: string): string[] =>
  [...source.matchAll(/from '([^']+)'/g)].map((match) => match[1] ?? '');

// What the element of the list may show of the account: its link, its network and state, its two amounts, its menu,
// and the expiry of its credentials (ADR-scadenza-nelle-pagine-chiavi-e-conti). The element is drawn in the shared Card,
// which shows nothing of the account (ADR-card-condivisa-distinta-dallo-sfondo).
const ITEM_PARTS = [
  'react',
  'react-router',
  '@/components/ui/card',
  '@/components/ui/details-list',
  '@/components/ui/network-notice',
  '@/config/paths',
  '../api/get-accounts',
  './account-actions',
  './account-amounts',
  './credentials-expiry',
  './detail',
  './reconciliation-state',
];
const ITEM_TERMS = ['Saldo (con risultato aperto)', 'Capitale libero'];
const ACCOUNT_TABS = ['Panoramica', 'Riconciliazione', 'Capitale', 'Impostazioni'];

const fileNamed = (files: readonly SourceFile[], path: string): SourceFile | undefined =>
  files.find((file) => file.path === path);

const missing = (files: readonly SourceFile[]): string[] =>
  PAGE_FILES.filter((path) => fileNamed(files, path) === undefined).map(
    (path) => `${path}: mancante`,
  );

/** What the element of the list shows beyond the parts the ADR names. */
const itemBeyondItsParts = (item: SourceFile): string[] => [
  ...importsOf(item.source)
    .filter((module) => !ITEM_PARTS.includes(module))
    .map((module) => `${item.path}: mostra ${module}`),
  ...[...item.source.matchAll(/term="([^"]+)"/g)]
    .map((match) => match[1] ?? '')
    .filter((term) => !ITEM_TERMS.includes(term))
    .map((term) => `${item.path}: mostra ${term}`),
];

const unless = (holds: boolean, violation: string): string[] => (holds ? [] : [violation]);

/** Each rule of the ADR the files of the list and of the page of the account break. */
const violationsOf = (files: readonly SourceFile[], longBoxExists: boolean): string[] => {
  const [item, actions, tabs, settings, page] = PAGE_FILES.map((path) => fileNamed(files, path));
  if (
    item === undefined ||
    actions === undefined ||
    tabs === undefined ||
    settings === undefined ||
    page === undefined
  ) {
    return missing(files);
  }
  const tabNames = [...tabs.source.matchAll(/name: '([^']+)'/g)].map((match) => match[1]);
  return [
    ...itemBeyondItsParts(item),
    ...unless(
      item.source.includes('paths.account.getHref(account.id)'),
      `${ITEM}: non porta alla pagina del conto`,
    ),
    ...unless(
      actions.source.includes("from '@/components/ui/actions-menu'"),
      `${ACTIONS}: azioni fuori dal menu «Azioni»`,
    ),
    ...unless(
      tabs.source.includes("from '@/components/ui/view-tabs'"),
      `${TABS}: non usa ViewTabs`,
    ),
    ...unless(
      JSON.stringify(tabNames) === JSON.stringify(ACCOUNT_TABS),
      `${TABS}: schede ${tabNames.join(', ')}`,
    ),
    ...unless(
      settings.source.includes("from '@/components/ui/danger-zone'") &&
        /<DangerZone[^>]*>[\s\S]*<RemoveAccount[\s\S]*<\/DangerZone>/.test(settings.source),
      `${SETTINGS}: rimozione fuori dalla DangerZone`,
    ),
    ...unless(
      page.source.includes('backTo={paths.accounts.getHref()}'),
      `${PAGE}: «Indietro» non porta ai conti`,
    ),
    ...unless(!longBoxExists, `${LONG_BOX}: il riquadro lungo esiste ancora`),
  ];
};

const file = (path: string, source: string): SourceFile => ({ path, source });

const conforming = (): SourceFile[] => [
  file(
    ITEM,
    `import { Link } from 'react-router';
     import { NetworkBadge } from '@/components/ui/network-notice';
     import { paths } from '@/config/paths';
     import { AccountActions } from './account-actions';
     import { AccountBalance, AccountFreeCapital } from './account-amounts';
     import { Detail } from './detail';
     import { ReconciliationState } from './reconciliation-state';
     <Link to={paths.account.getHref(account.id)} />
     <Detail term="Saldo (con risultato aperto)" /><Detail term="Capitale libero" />`,
  ),
  file(ACTIONS, "import { ActionsMenu } from '@/components/ui/actions-menu';"),
  file(
    TABS,
    `import { ViewTabs } from '@/components/ui/view-tabs';
     [{ name: 'Panoramica' }, { name: 'Riconciliazione' }, { name: 'Capitale' }, { name: 'Impostazioni' }]`,
  ),
  file(
    SETTINGS,
    `import { DangerZone } from '@/components/ui/danger-zone';
     <DangerZone title="Zona pericolosa"><RemoveAccount account={account} /></DangerZone>`,
  ),
  file(PAGE, '<DashboardLayout title={title} backTo={paths.accounts.getHref()}>'),
];

const replaced = (path: string, source: string): SourceFile[] =>
  conforming().map((candidate) => (candidate.path === path ? file(path, source) : candidate));

describe('ADR-elenco-dei-conti-e-pagina-del-conto: a compact list and a page of the account with tabs', () => {
  it('is silent on files that follow the ADR', () => {
    expect(violationsOf(conforming(), false)).toEqual([]);
  });

  it('is red when the element of the list shows the reconciliation or the value of the flows', () => {
    const [item] = conforming();
    const files = replaced(
      ITEM,
      `${item?.source ?? ''}
       import { ReconciliationStatus } from './reconciliation-status';
       <Detail term="Valore dei flussi" />`,
    );

    expect(violationsOf(files, false)).toEqual([
      `${ITEM}: mostra ./reconciliation-status`,
      `${ITEM}: mostra Valore dei flussi`,
    ]);
  });

  it('is red when the element of the list does not lead to the page of the account', () => {
    const [item] = conforming();
    const files = replaced(ITEM, (item?.source ?? '').replace('paths.account.', 'paths.accounts.'));

    expect(violationsOf(files, false)).toEqual([`${ITEM}: non porta alla pagina del conto`]);
  });

  it('is red when the actions are commands of the element instead of a menu', () => {
    const files = replaced(
      ACTIONS,
      "import { CommandButton } from '@/components/ui/command-button';",
    );

    expect(violationsOf(files, false)).toEqual([`${ACTIONS}: azioni fuori dal menu «Azioni»`]);
  });

  it('is red when the page of the account has tabs of its own, or other tabs', () => {
    const files = replaced(TABS, "<nav>[{ name: 'Panoramica' }, { name: 'Capitale' }]</nav>");

    expect(violationsOf(files, false)).toEqual([
      `${TABS}: non usa ViewTabs`,
      `${TABS}: schede Panoramica, Capitale`,
    ]);
  });

  it('is red when the removal stands outside the DangerZone', () => {
    const files = replaced(
      SETTINGS,
      `import { DangerZone } from '@/components/ui/danger-zone';
       <RemoveAccount account={account} /><DangerZone title="Zona pericolosa"></DangerZone>`,
    );

    expect(violationsOf(files, false)).toEqual([`${SETTINGS}: rimozione fuori dalla DangerZone`]);
  });

  it('is red when «Indietro» does not lead towards the accounts', () => {
    const files = replaced(PAGE, '<DashboardLayout title={title}>');

    expect(violationsOf(files, false)).toEqual([`${PAGE}: «Indietro» non porta ai conti`]);
  });

  it('is red when the long box of the account is still there', () => {
    expect(violationsOf(conforming(), true)).toEqual([
      `${LONG_BOX}: il riquadro lungo esiste ancora`,
    ]);
  });

  it('is red when a file of the list or of the page is missing', () => {
    expect(violationsOf(conforming().slice(1), false)).toEqual([`${ITEM}: mancante`]);
  });

  it('finds the list and the page of the account of the dashboard as the ADR decides', () => {
    expect(violationsOf(read(PAGE_FILES), existsSync(`${SOURCES}/${LONG_BOX}`))).toEqual([]);
  });
});
