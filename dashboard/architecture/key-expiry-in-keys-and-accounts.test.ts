// ADR-scadenza-nelle-pagine-chiavi-e-conti (R6.2.2): the expiry of every key shows through the shared component of
// src/components/ui/key-expiry.tsx, with its icon beside the text; the pages of the keys and of the accounts carry the
// shared notice at their head; the dashboard counts no day: state and days left are the API's.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

const DASHBOARD = fileURLToPath(new URL('..', import.meta.url));

type SourceFile = { readonly path: string; readonly source: string };

const SHARED = 'src/components/ui/key-expiry.tsx';
const KEYS = 'src/features/provider-keys/components/provider-keys-list.tsx';
const CREDENTIALS = 'src/features/accounts/components/credentials-expiry.tsx';
const ACCOUNT_ITEM = 'src/features/accounts/components/account-item.tsx';
const ACCOUNT_OVERVIEW = 'src/features/accounts/components/account-overview.tsx';
const ACCOUNTS_LIST = 'src/features/accounts/components/accounts-list.tsx';
const ACCOUNT_VIEW = 'src/features/accounts/components/account-view.tsx';
const DAY = 'src/utils/format-day.ts';
const FIELDS = 'src/types/key-expiry.ts';

const read = (path: string): SourceFile => ({
  path,
  source: readFileSync(`${DASHBOARD}${path}`, 'utf8'),
});

const file = (path: string, source: string): SourceFile => ({ path, source });

// What reading a clock or counting days looks like: the API gives the state and the days left.
const DAY_COUNTING = ['new Date(', 'Date.now', 'Date.parse', 'getTime(', 'differenceIn'];

const countingViolations = ({ path, source }: SourceFile): string[] =>
  DAY_COUNTING.filter((counting) => source.includes(counting)).map(
    (counting) => `${path}: conta i giorni da sé (${counting}), lo stato e i giorni sono dell'API`,
  );

/** Where a key shows its expiry: through the shared component, or the one of its feature that uses it. */
const showsExpiry =
  (component: string) =>
  ({ path, source }: SourceFile): string[] =>
    source.includes(`<${component}`) ? [] : [`${path}: non mostra la scadenza con <${component}>`];

/** Where a page warns of the keys to renew: at the head of what its component, the last of the file, returns. */
const warnsAtTheHead =
  (notice: string) =>
  ({ path, source }: SourceFile): string[] => {
    const at = source.indexOf(`<${notice}`);
    if (at === -1) {
      return [`${path}: non avvisa delle chiavi da rinnovare con <${notice}>`];
    }
    const firstElement = source.indexOf('<', source.lastIndexOf('return (') + 'return ('.length);
    const afterFragment = source.indexOf('<', firstElement + 1);
    return [firstElement, afterFragment].includes(at)
      ? []
      : [`${path}: l'avviso non sta in testa alla pagina`];
  };

/** The shared component draws its icons with the shared icon and never the colour alone. */
const sharedViolations = ({ path, source }: SourceFile): string[] => [
  ...(source.includes("from 'lucide-react'") ? [`${path}: disegna un'icona propria`] : []),
  ...(source.includes("from '@/features") ? [`${path}: importa una funzionalità`] : []),
  ...(["icon: 'triangle-alert'", "icon: 'circle-alert'"].every((icon) => source.includes(icon))
    ? []
    : [`${path}: lo stato in scadenza o scaduto non ha la sua icona`]),
  ...(source.includes('<Icon name={look.icon}')
    ? []
    : [`${path}: non usa l'icona condivisa accanto al testo`]),
];

const COUNTING = `const daysLeft = (expiry: string) => Math.ceil((new Date(expiry).getTime() - Date.now()) / 86400000);`;
const FROM_THE_API = `const headlineOf = ({ days_left }: KeyExpiry) => \`scade tra \${String(days_left)} giorni\`;`;

describe('the expiry of the keys in the pages of the keys and of the accounts', () => {
  it('ADR-scadenza-nelle-pagine-chiavi-e-conti: the rules tell a breach from a page that respects them', () => {
    expect(countingViolations(file(SHARED, COUNTING))).not.toEqual([]);
    expect(countingViolations(file(SHARED, FROM_THE_API))).toEqual([]);
    expect(showsExpiry('KeyExpiryStatus')(file(KEYS, '<span>{key.provider}</span>'))).not.toEqual(
      [],
    );
    expect(showsExpiry('KeyExpiryStatus')(file(KEYS, '<KeyExpiryStatus expiry={key} />'))).toEqual(
      [],
    );
    const below =
      'return (\n  <>\n    <ul></ul>\n    <ExpiringKeysNotice keys={keys} />\n  </>\n);';
    const above =
      'return (\n  <>\n    <ExpiringKeysNotice keys={keys} />\n    <ul></ul>\n  </>\n);';
    expect(warnsAtTheHead('ExpiringKeysNotice')(file(KEYS, below))).not.toEqual([]);
    expect(warnsAtTheHead('ExpiringKeysNotice')(file(KEYS, above))).toEqual([]);
    expect(warnsAtTheHead('ExpiringKeysNotice')(file(KEYS, '<ul></ul>'))).not.toEqual([]);
    expect(
      sharedViolations(file(SHARED, "import { TriangleAlert } from 'lucide-react';")),
    ).not.toEqual([]);
  });

  it('ADR-scadenza-nelle-pagine-chiavi-e-conti: the shared component draws its state with the shared icons', () => {
    expect(sharedViolations(read(SHARED))).toEqual([]);
  });

  it('ADR-scadenza-nelle-pagine-chiavi-e-conti: every key shows its expiry through the shared component', () => {
    expect([
      ...showsExpiry('KeyExpiryStatus')(read(KEYS)),
      ...showsExpiry('KeyExpiryStatus')(read(CREDENTIALS)),
      ...showsExpiry('CredentialsExpiryStatus')(read(ACCOUNT_ITEM)),
      ...showsExpiry('CredentialsExpiry')(read(ACCOUNT_OVERVIEW)),
    ]).toEqual([]);
  });

  it('ADR-scadenza-nelle-pagine-chiavi-e-conti: the pages of the keys and of the accounts warn at their head', () => {
    expect([
      ...warnsAtTheHead('ExpiringKeysNotice')(read(KEYS)),
      ...warnsAtTheHead('ExpiringCredentialsNotice')(read(ACCOUNTS_LIST)),
      ...warnsAtTheHead('ExpiringCredentialsNotice')(read(ACCOUNT_VIEW)),
    ]).toEqual([]);
  });

  it('ADR-scadenza-nelle-pagine-chiavi-e-conti: the dashboard counts no day of an expiry', () => {
    expect(
      [SHARED, KEYS, CREDENTIALS, DAY, FIELDS].flatMap((path) => countingViolations(read(path))),
    ).toEqual([]);
  });
});
