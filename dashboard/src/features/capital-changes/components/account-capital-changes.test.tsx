import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';

import { aCapitalChange, aTransfer } from '@/testing/mocks/capital-changes';
import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const AT = new Date('2026-11-15T09:07:00Z');
const HOUR = 3_600_000;

const rowsOf = async () => {
  const table = await screen.findByRole('table', { name: 'Variazioni di capitale' });
  return within(table).getAllByRole('row').slice(1);
};

// A missing row has no cells, so the comparison with the expected ones fails with both in sight.
const cellsOf = (row: HTMLElement | undefined) =>
  row === undefined
    ? []
    : within(row)
        .getAllByRole('cell')
        .map((cell) => cell.textContent);

// R3.4.2, ADR storico-delle-variazioni-di-capitale: the shared table and pages of the history of the capital.
describe('AccountCapitalChanges', () => {
  it('shows the changes of every flow of the account and its transfers, from the most recent', async () => {
    const alfa = fakePlatform.giveFlowTo('anna', 'alfa');
    const beta = fakePlatform.giveFlowTo('anna', 'beta');
    const accountId = alfa.accountId ?? '';
    fakePlatform.recordCapitalChange(
      aCapitalChange(alfa, 500, 700, new Date(AT.getTime() - 2 * HOUR)),
    );
    fakePlatform.recordCapitalChange(aCapitalChange(beta, 300, 200, new Date(AT.getTime() - HOUR)));
    fakePlatform.recordCapitalChange(aTransfer(accountId, 'deposito', 500, AT));
    await renderApp({ account: 'anna', url: `/accounts/${accountId}/capital` });

    const [deposit, reduction, increase] = await rowsOf();
    expect(cellsOf(deposit)).toEqual([
      'Data e ora15/11/2026, 10:07:00',
      'Flusso—',
      'Motivodeposito',
      'Importo500 USDC',
      'Capitale prima—',
      'Capitale dopo—',
    ]);
    expect(cellsOf(reduction)).toEqual([
      'Data e ora15/11/2026, 09:07:00',
      'Flussobeta',
      'Motivoriduzione',
      'Importo100 USDC',
      'Capitale prima300 USDC',
      'Capitale dopo200 USDC',
    ]);
    expect(cellsOf(increase)[1]).toBe('Flussoalfa');
  });

  // ADR elenco-dei-conti-e-pagina-del-conto: the history is the tab Capitale of the page of the account.
  it('is the tab Capitale of the page of the account, titled with its name', async () => {
    const accountId = fakePlatform.giveFlowTo('anna', 'alfa').accountId ?? '';
    await renderApp({ account: 'anna', url: `/accounts/${accountId}/capital` });

    expect(
      await screen.findByRole('heading', { level: 1, name: 'principale' }),
    ).toBeInTheDocument();
    expect(await screen.findByRole('link', { name: 'Capitale' })).toHaveAttribute(
      'aria-current',
      'page',
    );
  });

  it('shows only the changes of the minutes of the period', async () => {
    const alfa = fakePlatform.giveFlowTo('anna', 'alfa');
    const accountId = alfa.accountId ?? '';
    fakePlatform.recordCapitalChange(aTransfer(accountId, 'prelievo', 50, AT));
    fakePlatform.recordCapitalChange(
      aCapitalChange(alfa, 500, 700, new Date('2026-11-01T09:00:00Z')),
    );
    await renderApp({
      account: 'anna',
      url: `/accounts/${accountId}/capital?period=range&from=2026-11-14T00%3A00Z&to=2026-11-16T23%3A59Z`,
    });

    const rows = await rowsOf();
    expect(rows).toHaveLength(1);
    expect(rows[0]).toHaveTextContent('prelievo');
  });

  it('asks the start and the end of a range before reading', async () => {
    const accountId = fakePlatform.giveFlowTo('anna', 'alfa').accountId ?? '';
    await renderApp({
      account: 'anna',
      url: `/accounts/${accountId}/capital?period=range&from=2026-11-14`,
    });

    expect(
      await screen.findByText("Scegli l'inizio e la fine dell'intervallo."),
    ).toBeInTheDocument();
    expect(screen.queryByRole('table', { name: 'Variazioni di capitale' })).not.toBeInTheDocument();
  });

  it('tells why the history could not be read, as when the exchange does not answer', async () => {
    const accountId = fakePlatform.giveFlowTo('anna', 'alfa').accountId ?? '';
    server.use(
      http.get('*/accounts/:accountId/capital-changes', () =>
        HttpResponse.json({ detail: 'exchange non raggiungibile, riprovare' }, { status: 503 }),
      ),
    );
    await renderApp({ account: 'anna', url: `/accounts/${accountId}/capital` });

    expect(await screen.findByRole('alert')).toHaveTextContent('exchange non raggiungibile');
  });

  it('does not show the history of an account of someone else', async () => {
    fakePlatform.giveFlowTo('anna', 'alfa');
    await renderApp({ account: 'anna', url: '/accounts/account-of-bruno/capital' });

    // The page of the account reads the account first: an account of someone else is not found (ADR
    // elenco-dei-conti-e-pagina-del-conto).
    expect(await screen.findByText('Conto non trovato.')).toBeInTheDocument();
    expect(screen.queryByRole('table', { name: 'Variazioni di capitale' })).not.toBeInTheDocument();
  });
});
