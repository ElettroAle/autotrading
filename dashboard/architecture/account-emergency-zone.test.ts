// ADR-zona-di-emergenza-nella-pagina-del-conto (Bug 632): the emergency closing of an account stands in the «Zona di
// emergenza» at the bottom of the page of that account, with the shared DangerZone; the list of the accounts offers no
// emergency command.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

const SOURCES = fileURLToPath(new URL('../src', import.meta.url));

const ACCOUNT_PAGE = 'app/routes/app/account.tsx';
const ACCOUNTS_PAGE = 'app/routes/app/accounts.tsx';

const DANGER_ZONE = "from '@/components/ui/danger-zone'";
const EMERGENCY_COMMAND =
  "from '@/features/emergency-closing/components/emergency-closing-command'";

type Pages = { readonly account: string; readonly accounts: string };

const read = (path: string): string => readFileSync(`${SOURCES}/${path}`, 'utf8');

const unless = (holds: boolean, violation: string): string[] => (holds ? [] : [violation]);

/** The zone of the page of the account: a DangerZone with the emergency closing of that account in it. */
const zoneOfTheAccount = (source: string): boolean =>
  source.includes(DANGER_ZONE) &&
  source.includes(EMERGENCY_COMMAND) &&
  /<DangerZone>[\s\S]*<EmergencyClosingCommand[\s\S]*kind: 'account'[\s\S]*<\/DangerZone>/.test(
    source,
  );

/** The zone closes the page: nothing of the page follows it. */
const zoneAtTheBottom = (source: string): boolean =>
  /<AccountEmergencyZone [^>]*\/>\s*<\/DashboardLayout>/.test(source);

/** Each rule of the ADR the two pages break. */
const violationsOf = ({ account, accounts }: Pages): string[] => [
  ...unless(
    zoneOfTheAccount(account),
    `${ACCOUNT_PAGE}: la chiusura di emergenza del conto non sta nella DangerZone`,
  ),
  ...unless(zoneAtTheBottom(account), `${ACCOUNT_PAGE}: la zona di emergenza non è in fondo`),
  ...unless(
    !accounts.includes(EMERGENCY_COMMAND),
    `${ACCOUNTS_PAGE}: l'elenco dei conti offre la chiusura di emergenza`,
  ),
  ...unless(
    !accounts.includes(DANGER_ZONE),
    `${ACCOUNTS_PAGE}: l'elenco dei conti ha una DangerZone`,
  ),
];

const conforming = (): Pages => ({
  account: `import { DangerZone } from '@/components/ui/danger-zone';
    import { EmergencyClosingCommand } from '@/features/emergency-closing/components/emergency-closing-command';
    <DangerZone><EmergencyClosingCommand scope={{ kind: 'account', accountId }} /></DangerZone>
    <DashboardLayout title={title}>
      <AccountView accountId={accountId}>
        <AccountTabs accountId={accountId} />
        <Outlet />
      </AccountView>
      <AccountEmergencyZone accountId={accountId} />
    </DashboardLayout>`,
  accounts: `<AccountsList /><RegisterAccountForm />`,
});

describe('ADR-zona-di-emergenza-nella-pagina-del-conto: the emergency closing of an account on its page', () => {
  it('is silent on pages that follow the ADR', () => {
    expect(violationsOf(conforming())).toEqual([]);
  });

  it('is red when the page of the account has no zone with the emergency closing of the account', () => {
    const pages = {
      ...conforming(),
      account: `<DashboardLayout title={title}><AccountView accountId={accountId} /></DashboardLayout>`,
    };

    expect(violationsOf(pages)).toEqual([
      `${ACCOUNT_PAGE}: la chiusura di emergenza del conto non sta nella DangerZone`,
      `${ACCOUNT_PAGE}: la zona di emergenza non è in fondo`,
    ]);
  });

  it('is red when the emergency closing of the account stands outside the zone', () => {
    const { account } = conforming();
    const pages = {
      ...conforming(),
      account: account.replace(
        "<DangerZone><EmergencyClosingCommand scope={{ kind: 'account', accountId }} /></DangerZone>",
        "<EmergencyClosingCommand scope={{ kind: 'account', accountId }} /><DangerZone></DangerZone>",
      ),
    };

    expect(violationsOf(pages)).toEqual([
      `${ACCOUNT_PAGE}: la chiusura di emergenza del conto non sta nella DangerZone`,
    ]);
  });

  it('is red when the zone is not at the bottom of the page', () => {
    const { account } = conforming();
    const pages = {
      ...conforming(),
      account: account.replace(
        '</AccountView>\n      <AccountEmergencyZone accountId={accountId} />',
        '<AccountEmergencyZone accountId={accountId} />\n      </AccountView>',
      ),
    };

    expect(violationsOf(pages)).toEqual([`${ACCOUNT_PAGE}: la zona di emergenza non è in fondo`]);
  });

  it('is red when the list of the accounts offers the emergency closing', () => {
    const pages = {
      ...conforming(),
      accounts: `import { DangerZone } from '@/components/ui/danger-zone';
        import { EmergencyClosingCommand } from '@/features/emergency-closing/components/emergency-closing-command';`,
    };

    expect(violationsOf(pages)).toEqual([
      `${ACCOUNTS_PAGE}: l'elenco dei conti offre la chiusura di emergenza`,
      `${ACCOUNTS_PAGE}: l'elenco dei conti ha una DangerZone`,
    ]);
  });

  it('finds the pages of the accounts of the dashboard as the ADR decides', () => {
    expect(violationsOf({ account: read(ACCOUNT_PAGE), accounts: read(ACCOUNTS_PAGE) })).toEqual(
      [],
    );
  });
});
