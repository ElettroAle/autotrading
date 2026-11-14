import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { fakePlatform } from '@/testing/mocks/platform';
import { renderApp } from '@/testing/test-utils';

const DAY_MS = 24 * 60 * 60 * 1000;
const CYCLE_MS = 15 * 60 * 1000;

const daysAgo = (days: number) => new Date(Date.now() - days * DAY_MS);

const giveFlow = (
  name: string,
  equity: number[],
  { since = daysAgo(1), status = 'attivo' } = {},
) => {
  fakePlatform.addFlow('anna', name, { status });
  equity.forEach((value, index) => {
    fakePlatform.recordEquity(name, new Date(since.getTime() + index * CYCLE_MS), value);
  });
};

const table = () => screen.findByRole('table', { name: 'Classifica dei flussi' });

const rowNames = async () => {
  const rows = within(await table())
    .getAllByRole('row')
    .slice(1);
  return rows.map((row) => within(row).getByRole('link').textContent);
};

const cellOf = async (flow: string, header: string) => {
  const ranking = await table();
  const headers = within(ranking)
    .getAllByRole('columnheader')
    .map((cell) => cell.textContent?.replace(/[▲▼]/g, ''));
  const row = within(ranking)
    .getAllByRole('row')
    .find((candidate) => within(candidate).queryByRole('link', { name: flow }) !== null);
  return within(row as HTMLElement).getAllByRole('cell')[headers.indexOf(header)] as HTMLElement;
};

describe('FlowRanking', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
  });

  it('shows the flows from the highest return, with every value formatted in Italian', async () => {
    giveFlow('beta', [200, 210]);
    giveFlow('alfa', [300, 330, 297, 360]);
    fakePlatform
      .flowNamed('alfa')
      .history.closedPositions.push(
        { netPnl: 20, fees: 1, closedAt: daysAgo(1) },
        { netPnl: -6, fees: 0.5, closedAt: daysAgo(1) },
      );
    fakePlatform.flowNamed('alfa').history.modelCalls.push({ costUsd: 1.2, plannedAt: daysAgo(1) });
    await renderApp({ account: 'anna', url: '/ranking' });

    expect(await rowNames()).toEqual(['alfa', 'beta']);
    expect(await cellOf('alfa', 'Rendimento')).toHaveTextContent('+20,00%');
    expect(await cellOf('alfa', 'Drawdown massimo')).toHaveTextContent('10,00%');
    expect(await cellOf('alfa', 'PnL')).toHaveTextContent('+14 USDC');
    expect(await cellOf('alfa', 'Commissioni')).toHaveTextContent('1,5 USDC');
    expect(await cellOf('alfa', 'Win rate')).toHaveTextContent('50,00%');
    expect(await cellOf('alfa', 'Operazioni')).toHaveTextContent('2');
    expect(await cellOf('alfa', 'Costo del modello IA')).toHaveTextContent('1,20 USD');
    expect(await cellOf('beta', 'Win rate')).toHaveTextContent('non disponibile');
  });

  it('declares the default order on the return column', async () => {
    giveFlow('alfa', [100, 110]);
    await renderApp({ account: 'anna', url: '/ranking' });

    expect(within(await table()).getByRole('columnheader', { name: /Rendimento/ })).toHaveAttribute(
      'aria-sort',
      'descending',
    );
  });

  it('sorts by the column whose header is pressed, then turns the order', async () => {
    giveFlow('alfa', [300, 330, 297, 360]);
    giveFlow('beta', [200, 210]);
    const { router } = await renderApp({ account: 'anna', url: '/ranking' });
    await table();

    await userEvent.click(screen.getByRole('button', { name: 'Drawdown massimo' }));
    await waitFor(async () => expect(await rowNames()).toEqual(['alfa', 'beta']));
    await userEvent.click(screen.getByRole('button', { name: 'Drawdown massimo' }));

    await waitFor(async () => expect(await rowNames()).toEqual(['beta', 'alfa']));
    expect(screen.getByRole('columnheader', { name: /Drawdown massimo/ })).toHaveAttribute(
      'aria-sort',
      'ascending',
    );
    expect(router.state.location.search).toBe('?sort=drawdown&order=asc');
  });

  it('reads the order from the query string and forgets it back to the default', async () => {
    giveFlow('alfa', [300, 360]);
    giveFlow('beta', [200, 210]);
    const { router } = await renderApp({ account: 'anna', url: '/ranking?sort=return&order=asc' });

    expect(await rowNames()).toEqual(['beta', 'alfa']);
    await userEvent.click(screen.getByRole('button', { name: 'Rendimento' }));

    await waitFor(async () => expect(await rowNames()).toEqual(['alfa', 'beta']));
    expect(router.state.location.search).toBe('');
  });

  it('ignores an order on a column it does not know', async () => {
    giveFlow('alfa', [300, 360]);
    giveFlow('beta', [200, 210]);
    await renderApp({ account: 'anna', url: '/ranking?sort=colore&order=asc' });

    expect(await rowNames()).toEqual(['alfa', 'beta']);
  });

  it('reads the ranking of the period of the page', async () => {
    giveFlow('alfa', [100, 110]);
    giveFlow('gamma', [100, 500], { since: daysAgo(20) });
    await renderApp({ account: 'anna', url: '/ranking' });
    expect(await rowNames()).toEqual(['gamma', 'alfa']);

    await userEvent.selectOptions(screen.getByLabelText('Periodo'), '7 giorni');

    await waitFor(async () => expect(await rowNames()).toEqual(['alfa']));
  });

  it('leaves out the archived flows', async () => {
    giveFlow('alfa', [100, 110]);
    giveFlow('vecchio', [100, 400], { status: 'archiviato' });
    await renderApp({ account: 'anna', url: '/ranking' });

    expect(await rowNames()).toEqual(['alfa']);
  });

  it('says when no flow has cycles in the period', async () => {
    await renderApp({ account: 'anna', url: '/ranking' });

    expect(await screen.findByText('Nessun flusso con cicli nel periodo.')).toBeInTheDocument();
  });

  it('waits for both days of a range', async () => {
    await renderApp({ account: 'anna', url: '/ranking?period=range&from=2026-11-01' });

    expect(
      await screen.findByText("Scegli il primo e l'ultimo giorno dell'intervallo."),
    ).toBeInTheDocument();
  });

  it('tells why the ranking could not be read', async () => {
    await renderApp({
      account: 'anna',
      url: '/ranking?period=range&from=2026-11-03&to=2026-11-01',
    });

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'periodo non valido: il giorno iniziale è successivo al giorno finale',
    );
  });

  describe('choosing the flows to compare', () => {
    const SIX = ['uno', 'due', 'tre', 'quattro', 'cinque', 'sei'];

    it('keeps the flows chosen in the query string and links to their curves with the period', async () => {
      giveFlow('alfa', [100, 110]);
      giveFlow('beta', [100, 105]);
      const { router } = await renderApp({ account: 'anna', url: '/ranking?period=30d' });
      await table();

      await userEvent.click(screen.getByRole('checkbox', { name: 'Confronta alfa' }));
      await userEvent.click(screen.getByRole('checkbox', { name: 'Confronta beta' }));

      await waitFor(() =>
        expect(router.state.location.search).toBe('?period=30d&flows=flow-alfa%2Cflow-beta'),
      );
      expect(screen.getByRole('link', { name: 'Confronta le curve' })).toHaveAttribute(
        'href',
        '/comparison?period=30d&flows=flow-alfa%2Cflow-beta',
      );
    });

    it('lets a flow chosen be left out again', async () => {
      giveFlow('alfa', [100, 110]);
      const { router } = await renderApp({ account: 'anna', url: '/ranking?flows=flow-alfa' });

      await userEvent.click(await screen.findByRole('checkbox', { name: 'Confronta alfa' }));

      await waitFor(() => expect(router.state.location.search).toBe(''));
      expect(screen.queryByRole('link', { name: 'Confronta le curve' })).not.toBeInTheDocument();
    });

    it('offers no sixth flow once five are chosen', async () => {
      SIX.forEach((name, index) => giveFlow(name, [100, 110 + index]));
      const chosen = SIX.slice(0, 5)
        .map((name) => `flow-${name}`)
        .join(',');
      await renderApp({ account: 'anna', url: `/ranking?flows=${chosen}` });

      expect(await screen.findByRole('checkbox', { name: 'Confronta sei' })).toBeDisabled();
      expect(screen.getByRole('checkbox', { name: 'Confronta uno' })).toBeChecked();
      expect(screen.getByRole('checkbox', { name: 'Confronta uno' })).toBeEnabled();
    });
  });
});
