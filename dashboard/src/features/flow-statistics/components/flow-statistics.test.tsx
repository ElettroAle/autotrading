import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { fakePlatform, type FakeFlowHistory } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const DAY_MS = 24 * 60 * 60 * 1000;
const daysAgo = (days: number) => new Date(Date.now() - days * DAY_MS);

const ALFA: FakeFlowHistory = {
  closedPositions: [
    { netPnl: 20, fees: 0.75, closedAt: daysAgo(20) },
    { netPnl: 10, fees: 0.75, closedAt: daysAgo(20) },
    { netPnl: -6, fees: 0.75, closedAt: daysAgo(20) },
    { netPnl: -4, fees: 0.75, closedAt: daysAgo(2) },
  ],
  modelCalls: [{ costUsd: 1.2, plannedAt: daysAgo(20) }],
};

const panel = () => screen.findByRole('region', { name: 'Statistiche' });

const valueOf = async (label: string) =>
  within(await panel()).findByLabelText(label, { exact: true });

const shownNow = (label: string) =>
  within(screen.getByRole('region', { name: 'Statistiche' })).getByLabelText(label, {
    exact: true,
  });

describe('FlowStatistics', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
  });

  it('shows every statistic of the flow formatted in Italian', async () => {
    fakePlatform.addFlow('anna', 'alfa', { history: ALFA });
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await valueOf('Operazioni vinte')).toHaveTextContent('2');
    expect(await valueOf('Operazioni perse')).toHaveTextContent('2');
    expect(await valueOf('Win rate')).toHaveTextContent('50,00%');
    expect(await valueOf('PnL medio delle vincenti')).toHaveTextContent('+15 USDC');
    expect(await valueOf('PnL medio delle perdenti')).toHaveTextContent('-5 USDC');
    expect(await valueOf('Commissioni totali')).toHaveTextContent('3 USDC');
    expect(await valueOf('Numero di operazioni')).toHaveTextContent('4');
    expect(await valueOf('Costo del modello IA')).toHaveTextContent('1,20 USD');
  });

  it('says what is not available without operations', async () => {
    fakePlatform.addFlow('anna', 'beta');
    await renderApp({ account: 'anna', url: '/flows/flow-beta' });

    expect(await valueOf('Numero di operazioni')).toHaveTextContent('0');
    expect(await valueOf('Win rate')).toHaveTextContent('non disponibile');
    expect(await valueOf('PnL medio delle vincenti')).toHaveTextContent('non disponibile');
    expect(await valueOf('PnL medio delle perdenti')).toHaveTextContent('non disponibile');
  });

  it('reads the statistics of the period of the page', async () => {
    fakePlatform.addFlow('anna', 'alfa', { history: ALFA });
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });
    await valueOf('Numero di operazioni');

    await userEvent.selectOptions(screen.getByLabelText('Periodo'), '7 giorni');

    await waitFor(() => expect(shownNow('Numero di operazioni')).toHaveTextContent('1'));
    expect(shownNow('Operazioni vinte')).toHaveTextContent('0');
    expect(shownNow('Operazioni perse')).toHaveTextContent('1');
  });

  it('says how many model calls have no known cost', async () => {
    fakePlatform.addFlow('anna', 'alfa', { history: ALFA });
    server.use(
      http.get('*/flows/:flowId/statistics', () =>
        HttpResponse.json({
          won: 0,
          lost: 0,
          operations: 0,
          win_rate_percent: null,
          average_winning_pnl: null,
          average_losing_pnl: null,
          total_fees: '0',
          model_cost_usd: '0.5',
          model_calls_without_cost: 2,
        }),
      ),
    );
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await valueOf('Costo del modello IA')).toHaveTextContent(
      '0,50 USD (2 chiamate senza costo noto)',
    );
  });

  it('waits for both days of a range', async () => {
    fakePlatform.addFlow('anna', 'alfa', { history: ALFA });
    await renderApp({ account: 'anna', url: '/flows/flow-alfa?period=range&from=2026-11-01' });

    expect(await panel()).toHaveTextContent("Scegli il primo e l'ultimo giorno dell'intervallo.");
  });

  it('tells why the statistics could not be read', async () => {
    fakePlatform.addFlow('anna', 'alfa', { history: ALFA });
    await renderApp({
      account: 'anna',
      url: '/flows/flow-alfa?period=range&from=2026-11-03&to=2026-11-01',
    });

    expect(await within(await panel()).findByRole('alert')).toHaveTextContent(
      'periodo non valido: il giorno iniziale è successivo al giorno finale',
    );
  });
});
