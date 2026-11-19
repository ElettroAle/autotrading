import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { fakePlatform } from '@/testing/mocks/platform';
import { fakeReconciliation, type FakeUnattributable } from '@/testing/mocks/reconciliation';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';
import { formatInstant } from '@/utils/format-instant';

// The record is in the tab Riconciliazione of the page of the account (ADR elenco-dei-conti-e-pagina-del-conto).
const RECONCILIATION_TAB = '/accounts/account-test-1/reconciliation';
const ACCOUNT_ID = 'account-test-1';
const HOUR_MS = 60 * 60 * 1000;

const hoursAgo = (hours: number): string => new Date(Date.now() - hours * HOUR_MS).toISOString();

const change = (hours: number, amount: string): FakeUnattributable => ({
  detected_at: hoursAgo(hours),
  kind: 'variazione del saldo',
  asset: null,
  amount,
});

const position = (hours: number, asset: string): FakeUnattributable => ({
  detected_at: hoursAgo(hours),
  kind: 'posizione',
  asset,
  amount: '1.5',
});

const record = (...cases: FakeUnattributable[]): void => {
  cases.forEach((recorded) => fakeReconciliation.recordUnattributable(ACCOUNT_ID, recorded));
};

const MOVEMENTS = 'Movimenti non spiegati del conto test-1';

const movements = (): Promise<HTMLElement> => screen.findByRole('region', { name: MOVEMENTS });

const table = async (): Promise<HTMLElement> =>
  within(await movements()).findByRole('table', { name: 'Movimenti non spiegati' });

const rowsOf = (shown: HTMLElement): string[] =>
  within(shown)
    .getAllByRole('row')
    .slice(1)
    .map((row) => row.textContent ?? '');

describe('UnattributableMovements', () => {
  beforeEach(() => {
    fakePlatform.giveAccountTo('anna', 'test-1', 1000);
  });

  it('lists the cases of the last 24 hours, the most recent first, with the net of the changes above the table', async () => {
    const recent = change(1, '0.05');
    record(change(30, '-9'), position(2, 'SOL'), recent, change(3, '-0.03'));
    await renderApp({ account: 'anna', url: RECONCILIATION_TAB });

    const shown = await table();
    expect(
      within(shown)
        .getAllByRole('columnheader')
        .map((header) => header.textContent),
    ).toEqual(['Rilevato il', 'Tipo', 'Asset', 'Importo']);
    expect(rowsOf(shown)).toEqual([
      expect.stringContaining('Variazione del saldo'),
      expect.stringContaining('Posizione'),
      expect.stringContaining('Variazione del saldo'),
    ]);
    const [first] = within(shown).getAllByRole('row').slice(1);
    expect(first).toHaveTextContent(formatInstant(recent.detected_at));
    expect(first).toHaveTextContent('0,05 USDC');
    expect(rowsOf(shown)[1]).toContain('SOL');
    expect(rowsOf(shown)[1]).toContain('1,5');
    const section = await movements();
    expect(
      within(section).getByText('Totale netto delle variazioni: 0,02 USDC'),
    ).toBeInTheDocument();
    expect(within(section).getByText('3 movimenti')).toBeInTheDocument();
  });

  it('comes right after the section of the reconciliation in the tab of the account', async () => {
    await renderApp({ account: 'anna', url: RECONCILIATION_TAB });

    const section = await movements();
    const sections = within(screen.getByRole('main'))
      .getAllByRole('region', { name: /del conto test-1$/ })
      .map((region) => region.getAttribute('aria-label'));
    expect(sections).toEqual([
      'Riconciliazione del conto test-1',
      'Movimenti non spiegati del conto test-1',
    ]);
    expect(
      within(section).getByRole('heading', { name: 'Movimenti non spiegati' }),
    ).toBeInTheDocument();
  });

  it('says when nothing is unexplained in the period', async () => {
    record(change(30, '-9'));
    await renderApp({ account: 'anna', url: RECONCILIATION_TAB });

    const section = await movements();
    expect(
      await within(section).findByText('Nessun movimento non spiegato nel periodo'),
    ).toBeInTheDocument();
    expect(within(section).getByText('Totale netto delle variazioni: 0 USDC')).toBeInTheDocument();
  });

  it('narrows the cases by kind with the shared filters', async () => {
    record(change(1, '0.05'), position(2, 'SOL'));
    await renderApp({ account: 'anna', url: RECONCILIATION_TAB });
    await table();

    await userEvent.click(within(await movements()).getByRole('button', { name: 'Posizioni' }));

    const section = await movements();
    expect(await within(section).findByText('1 movimento')).toBeInTheDocument();
    expect(rowsOf(await table())).toEqual([expect.stringContaining('SOL')]);
  });

  it('widens the period with the shared filters', async () => {
    record(change(1, '0.05'), change(30, '-9'));
    await renderApp({ account: 'anna', url: RECONCILIATION_TAB });
    await table();

    await userEvent.click(within(await movements()).getByRole('button', { name: '7 giorni' }));

    const section = await movements();
    expect(await within(section).findByText('2 movimenti')).toBeInTheDocument();
    expect(
      within(section).getByText('Totale netto delle variazioni: -8,95 USDC'),
    ).toBeInTheDocument();
  });

  it('keeps the last 24 hours for a period the record does not offer', async () => {
    record(change(1, '0.05'), change(30, '-9'));
    await renderApp({ account: 'anna', url: `${RECONCILIATION_TAB}?${ACCOUNT_ID}.period=range` });

    expect(rowsOf(await table())).toHaveLength(1);
  });

  it('says why the record cannot be read', async () => {
    server.use(
      http.get('*/accounts/:accountId/reconciliation/unattributable', () =>
        HttpResponse.json(
          { type: 'about:blank', title: 'Error', status: 500, detail: 'errore interno' },
          { status: 500, headers: { 'Content-Type': 'application/problem+json' } },
        ),
      ),
    );
    await renderApp({ account: 'anna', url: RECONCILIATION_TAB });

    expect(await within(await movements()).findByRole('alert')).toBeInTheDocument();
  });

  it('reads the next page with the command Altri, until the last one', async () => {
    record(...Array.from({ length: 51 }, (_, minute) => change(minute / 60, '1')));
    await renderApp({ account: 'anna', url: RECONCILIATION_TAB });
    expect(rowsOf(await table())).toHaveLength(50);

    await userEvent.click(within(await movements()).getByRole('button', { name: 'Altri' }));

    // The rows already shown answer at once: the last page has arrived only when «Altri» is gone (Bug 628).
    await waitFor(() => {
      expect(
        within(screen.getByRole('region', { name: MOVEMENTS })).queryByRole('button', {
          name: 'Altri',
        }),
      ).toBeNull();
    });
    expect(rowsOf(await table())).toHaveLength(51);
  });
});
