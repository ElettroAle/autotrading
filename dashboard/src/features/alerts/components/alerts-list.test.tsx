import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { fakeAlerts } from '@/testing/mocks/alerts';
import { fakePlatform } from '@/testing/mocks/platform';
import { fakeReconciliation } from '@/testing/mocks/reconciliation';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';
import { formatInstant } from '@/utils/format-instant';

const ALERTS_PAGE = '/alerts';
const ACCOUNT_ID = 'account-test-1';
const MINUTE_MS = 60 * 1000;
const HOUR_MS = 60 * MINUTE_MS;

const hoursAgo = (hours: number): Date => new Date(Date.now() - hours * HOUR_MS);

const pauseOf = (account: string, flow: string, at: Date) => {
  const paused = fakePlatform.addFlow(account, flow, { status: 'in pausa' });
  return fakeAlerts.open(
    fakePlatform.user(account).tenantId,
    'flow_paused',
    { kind: 'flow', id: paused.id, name: flow },
    [{ label: 'Motivo', value: 'credito esaurito' }],
    at,
  );
};

const fillOf = (account: string, asset: string, at: Date) =>
  fakeAlerts.open(
    fakePlatform.user(account).tenantId,
    'unattributable_fill',
    { kind: 'account', id: ACCOUNT_ID, name: 'test-1' },
    [{ label: 'Asset', value: asset }],
    at,
  );

const table = (): Promise<HTMLElement> => screen.findByRole('table', { name: 'Avvisi' });

const rowsOf = (shown: HTMLElement): HTMLElement[] => within(shown).getAllByRole('row').slice(1);

const choose = async (filter: string, choice: string) => {
  const group = screen.getByRole('group', { name: filter });
  await userEvent.click(within(group).getByRole('button', { name: choice }));
};

describe('AlertsList', () => {
  beforeEach(() => {
    fakePlatform.giveAccountTo('anna', 'test-1', 1000);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('lists the open alerts of every source, the newest first, with severity, resource, opening and state', async () => {
    fakeReconciliation.openAlarm(ACCOUNT_ID, 1000, 980, hoursAgo(2));
    const pause = pauseOf('anna', 'alfa', hoursAgo(1));
    await renderApp({ account: 'anna', url: ALERTS_PAGE });

    const shown = await table();
    expect(
      within(shown)
        .getAllByRole('columnheader')
        .map((header) => header.textContent),
    ).toEqual(['Gravità', 'Avviso', 'Risorsa interessata', 'Aperto il', 'Stato']);
    const [first, second] = rowsOf(shown);
    expect(first).toHaveTextContent('Flusso in pausa automatica');
    expect(first).toHaveTextContent(formatInstant(pause.opened_at));
    expect(first).toHaveTextContent('Aperto');
    expect(within(first ?? shown).getByText('Critica')).toHaveClass('text-red-700');
    expect(within(first ?? shown).getByRole('link', { name: 'Flusso alfa' })).toHaveAttribute(
      'href',
      '/flows/flow-alfa',
    );
    expect(second).toHaveTextContent('Allarme di riconciliazione');
    expect(within(second ?? shown).getByRole('link', { name: 'Conto test-1' })).toHaveAttribute(
      'href',
      `/accounts/${ACCOUNT_ID}`,
    );
    expect(screen.getByText('2 avvisi')).toBeInTheDocument();
  });

  it('shows a warning in amber and leads from a row to the detail of the alert', async () => {
    const fill = fillOf('anna', 'SOL', hoursAgo(1));
    await renderApp({ account: 'anna', url: ALERTS_PAGE });

    const [row] = rowsOf(await table());
    expect(within(row ?? document.body).getByText('Attenzione')).toHaveClass('text-amber-700');
    expect(within(row ?? document.body).getByRole('link', { name: 'Attenzione' })).toHaveAttribute(
      'href',
      `/alerts/${fill.id}`,
    );
  });

  it('opens on the open alerts and shows the resolved ones, with when, on request', async () => {
    fillOf('anna', 'SOL', hoursAgo(2));
    const resolved = fillOf('anna', 'ETH', hoursAgo(1));
    fakeAlerts.resolveByHand('tenant-anna', resolved.id, hoursAgo(0.5));
    await renderApp({ account: 'anna', url: ALERTS_PAGE });

    expect(rowsOf(await table())).toHaveLength(1);
    await choose('Filtri di Avvisi', 'Tutti');

    await screen.findByText('2 avvisi');
    const [first] = rowsOf(await table());
    expect(first).toHaveTextContent(`Risolto il ${formatInstant(resolved.resolved_at ?? '')}`);
  });

  it('narrows the list by severity, kind of resource and period', async () => {
    pauseOf('anna', 'alfa', hoursAgo(1));
    fillOf('anna', 'SOL', hoursAgo(48));
    await renderApp({ account: 'anna', url: ALERTS_PAGE });
    await table();

    await choose('Filtri di Avvisi', 'Attenzione');
    await screen.findByText('1 avviso');
    expect(rowsOf(await table())[0]).toHaveTextContent('Esecuzione senza identificativo');

    await userEvent.click(screen.getByRole('button', { name: 'Azzera i filtri' }));
    await choose('Filtri di Avvisi', 'Flusso');
    await screen.findByText('1 avviso');
    expect(rowsOf(await table())[0]).toHaveTextContent('Flusso in pausa automatica');

    await userEvent.click(screen.getByRole('button', { name: 'Azzera i filtri' }));
    await choose('Filtri di Avvisi', '24 ore');
    await screen.findByText('1 avviso');
    expect(rowsOf(await table())[0]).toHaveTextContent('Flusso in pausa automatica');
  });

  it('lists the alerts of one resource in every state from its link', async () => {
    fakeReconciliation.closedAlarm(ACCOUNT_ID, hoursAgo(3), hoursAgo(2));
    pauseOf('anna', 'alfa', hoursAgo(1));
    await renderApp({ account: 'anna', url: `/alerts?resource_id=${ACCOUNT_ID}&state=all` });

    const rows = rowsOf(await table());
    expect(rows).toHaveLength(1);
    expect(rows[0]).toHaveTextContent('Allarme di riconciliazione');
    expect(rows[0]).toHaveTextContent('Risolto il');
  });

  it('leads an alert on a key to the keys', async () => {
    fakeAlerts.open(
      'tenant-anna',
      'unattributable_fill',
      { kind: 'key', id: 'key-openrouter', name: 'openrouter' },
      [],
      hoursAgo(1),
    );
    await renderApp({ account: 'anna', url: ALERTS_PAGE });

    expect(within(await table()).getByRole('link', { name: 'Chiave openrouter' })).toHaveAttribute(
      'href',
      '/provider-keys',
    );
  });

  it('says when no alert is open', async () => {
    await renderApp({ account: 'anna', url: ALERTS_PAGE });

    expect(await screen.findByText('Nessun avviso aperto')).toBeInTheDocument();
  });

  it('shows the alerts of the user only', async () => {
    fakePlatform.giveAccountTo('bruno', 'test-2', 1000);
    fakeAlerts.open(
      fakePlatform.user('bruno').tenantId,
      'unattributable_fill',
      { kind: 'account', id: 'account-test-2', name: 'test-2' },
      [],
      hoursAgo(1),
    );
    await renderApp({ account: 'anna', url: ALERTS_PAGE });

    expect(await screen.findByText('Nessun avviso aperto')).toBeInTheDocument();
  });

  it('reads the next page on request', async () => {
    Array.from({ length: 51 }, (_, index) => fillOf('anna', `A${index}`, hoursAgo(index + 1)));
    await renderApp({ account: 'anna', url: ALERTS_PAGE });

    expect(rowsOf(await table())).toHaveLength(50);
    await userEvent.click(screen.getByRole('button', { name: 'Altri' }));

    const shown = await table();
    await waitFor(() => expect(rowsOf(shown)).toHaveLength(51));
    expect(screen.queryByRole('button', { name: 'Altri' })).toBeNull();
  });

  // ADR intervallo-delle-liste-fissato-alla-scelta-del-periodo: the period is counted from when it was chosen, so a
  // minute that passes before «Altri» adds the next page to those read.
  it('adds the next page to those read when a minute passes before Altri', async () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    Array.from({ length: 51 }, (_, index) => fillOf('anna', `A${index}`, hoursAgo(index / 60)));
    await renderApp({ account: 'anna', url: `${ALERTS_PAGE}?period=24h` });
    expect(rowsOf(await table())).toHaveLength(50);

    vi.setSystemTime(Date.now() + MINUTE_MS);
    await userEvent.click(screen.getByRole('button', { name: 'Altri' }));

    await waitFor(() => expect(screen.queryByRole('button', { name: 'Altri' })).toBeNull());
    expect(rowsOf(await table())).toHaveLength(51);
  });

  it('tells when the alerts cannot be read', async () => {
    server.use(http.get('*/alerts', () => HttpResponse.json({}, { status: 500 })));
    await renderApp({ account: 'anna', url: ALERTS_PAGE });

    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });

  it('shows the number of the open alerts beside the entry of the menu', async () => {
    fakeReconciliation.openAlarm(ACCOUNT_ID, 1000, 980, hoursAgo(2));
    pauseOf('anna', 'alfa', hoursAgo(1));
    await renderApp({ account: 'anna', url: ALERTS_PAGE });
    await table();

    const navigation = screen.getByRole('navigation', { name: 'Navigazione' });
    expect(
      await within(navigation).findByRole('link', { name: /^Avvisi\s*2\s*aperti$/ }),
    ).toBeInTheDocument();
  });

  it('shows no number beside the entry of the menu with no alert open', async () => {
    await renderApp({ account: 'anna', url: ALERTS_PAGE });
    await screen.findByText('Nessun avviso aperto');

    const navigation = screen.getByRole('navigation', { name: 'Navigazione' });
    expect(within(navigation).getByRole('link', { name: 'Avvisi' })).toHaveTextContent(/^Avvisi$/);
  });

  it('leads the alarms of an account of before to its alerts in every state', async () => {
    fakeReconciliation.closedAlarm(ACCOUNT_ID, hoursAgo(3), hoursAgo(2));
    const { router } = await renderApp({ account: 'anna', url: `/accounts/${ACCOUNT_ID}/alarms` });

    expect(rowsOf(await table())).toHaveLength(1);
    expect(router.state.location.pathname).toBe('/alerts');
    expect(router.state.location.search).toBe(`?resource_id=${ACCOUNT_ID}&state=all`);
  });
});
