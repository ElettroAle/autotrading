import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { aCompletedCycle, aFailedCycle, STEPS, withDecisions } from '@/testing/mocks/cycles';
import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

// R6.5.5 (ADR scheda-decisioni-nella-pagina-del-flusso): the tab Decisioni of the page of the flow.

const LAST = new Date('2026-11-14T09:07:00Z');
const HOUR = 3_600_000;
const LONG_REASONING =
  'Il prezzo ha rotto la resistenza con volumi in aumento e il sentiment resta positivo: apro una posizione long ' +
  'con leva contenuta e uno stop sotto il minimo della giornata, pronto a chiuderla se il volume cala.';

const hoursBack = (hours: number) => new Date(LAST.getTime() - hours * HOUR);

const decidedCycles = () => [
  withDecisions(aCompletedCycle(hoursBack(0)), [
    { asset: 'ETH', action: 'mantieni', reasoning: 'attesa', confidence: 40, opening: null },
    {
      asset: 'BTC',
      action: 'apri',
      reasoning: LONG_REASONING,
      confidence: 72,
      opening: { direction: 'long' },
    },
  ]),
  withDecisions(aCompletedCycle(hoursBack(1)), [
    { asset: 'BTC', action: 'chiudi', reasoning: 'obiettivo raggiunto', opening: null },
  ]),
];

const rowsOf = async () => {
  const table = await screen.findByRole('table', { name: 'Decisioni' });
  return within(table).getAllByRole('row').slice(1);
};

const cellOf = (row: HTMLElement, column: number): HTMLElement =>
  within(row).getAllByRole('cell')[column] as HTMLElement;

describe('DecisionsTable', () => {
  beforeEach(() => {
    fakePlatform.giveFlowTo('anna', 'alfa');
    fakePlatform.changeFlow('alfa', { assets: ['BTC', 'ETH'] });
  });

  it('lists one row per cycle and asset, newest first, with every column', async () => {
    fakePlatform.recordCycles('alfa', decidedCycles());
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/decisions' });

    const rows = await rowsOf();
    expect(rows).toHaveLength(3);
    const [first, second, third] = rows as [HTMLElement, HTMLElement, HTMLElement];
    expect(cellOf(first, 0)).toHaveTextContent('14/11/2026, 10:07:00');
    expect(cellOf(first, 1)).toHaveTextContent('BTC');
    expect(cellOf(first, 2)).toHaveTextContent('apri');
    expect(cellOf(first, 3)).toHaveTextContent('long');
    expect(cellOf(first, 4)).toHaveTextContent('72');
    expect(cellOf(second, 1)).toHaveTextContent('ETH');
    expect(cellOf(second, 3)).toHaveTextContent('—');
    expect(cellOf(third, 0)).toHaveTextContent('14/11/2026, 09:07:00');
    expect(cellOf(third, 4)).toHaveTextContent('non disponibile');
    expect(screen.getByText('3 decisioni')).toBeInTheDocument();
  });

  it('shortens the reasoning, which the detail of the cycle shows whole', async () => {
    fakePlatform.recordCycles('alfa', decidedCycles());
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/decisions' });

    const [first] = (await rowsOf()) as [HTMLElement];
    const reasoning = cellOf(first, 5).textContent ?? '';
    expect(reasoning.endsWith('…')).toBe(true);
    expect(LONG_REASONING.includes(reasoning.replace('Ragionamento', '').slice(0, -1))).toBe(true);
  });

  it('shows the action and the direction with their icons (R6.5.3)', async () => {
    fakePlatform.recordCycles('alfa', decidedCycles());
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/decisions' });

    const [first] = (await rowsOf()) as [HTMLElement];
    expect(
      within(within(first).getByText('apri')).getByRole('img', { hidden: true }),
    ).toHaveAttribute('data-icon', 'plus');
    expect(
      within(within(first).getByText('long')).getByRole('img', { hidden: true }),
    ).toHaveAttribute('data-icon', 'arrow-up');
  });

  it('leads from each row to the detail of its cycle', async () => {
    fakePlatform.recordCycles('alfa', decidedCycles());
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/decisions' });

    const [first] = (await rowsOf()) as [HTMLElement];
    expect(within(first).getByRole('link', { name: '14/11/2026, 10:07:00' })).toHaveAttribute(
      'href',
      '/flows/flow-alfa/cycles/2026-11-14T09%3A07%3A00Z',
    );
  });

  it('leaves out the decisions of a cycle that failed after deciding', async () => {
    const latest = withDecisions(aCompletedCycle(hoursBack(0)), [
      { asset: 'BTC', action: 'mantieni', reasoning: 'attesa', confidence: 40, opening: null },
    ]);
    fakePlatform.recordCycles('alfa', [
      aFailedCycle(latest, STEPS.riskCheck, { errorType: 'X', message: 'y' }),
    ]);
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/decisions' });

    expect(await screen.findByText('Nessuna decisione registrata.')).toBeInTheDocument();
  });

  it('keeps the filters in the address and asks the API for them', async () => {
    fakePlatform.recordCycles('alfa', decidedCycles());
    const user = userEvent.setup();
    const { router } = await renderApp({ account: 'anna', url: '/flows/flow-alfa/decisions' });
    await rowsOf();

    const actions = screen.getByRole('group', { name: 'Azione' });
    await user.click(within(actions).getByRole('button', { name: 'Apri' }));
    await user.click(
      within(screen.getByRole('group', { name: 'Direzione' })).getByRole('button', {
        name: 'Long',
      }),
    );

    await screen.findByText('1 decisione');
    expect(router.state.location.search).toBe('?action=apri&direction=long');
    expect(await rowsOf()).toHaveLength(1);
  });

  it('filters by the assets of the flow', async () => {
    fakePlatform.recordCycles('alfa', decidedCycles());
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/decisions?asset=ETH' });

    const rows = await rowsOf();
    expect(rows).toHaveLength(1);
    expect(
      within(screen.getByRole('group', { name: 'Asset' })).getByRole('button', { name: 'ETH' }),
    ).toHaveAttribute('aria-pressed', 'true');
  });

  it('says no decision matches the filters', async () => {
    fakePlatform.recordCycles('alfa', decidedCycles());
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/decisions?action=aggiorna' });

    expect(await screen.findByText('Nessuna decisione con questi filtri.')).toBeInTheDocument();
  });

  it('follows the period of the page', async () => {
    fakePlatform.recordCycles('alfa', decidedCycles());
    await renderApp({
      account: 'anna',
      url: '/flows/flow-alfa/decisions?period=range&from=2026-11-14T08:07Z&to=2026-11-14T08:07Z',
    });

    const rows = await rowsOf();
    expect(rows).toHaveLength(1);
    expect(cellOf(rows[0] as HTMLElement, 2)).toHaveTextContent('chiudi');
  });

  it('asks the API for the last 7 days, which the API counts', async () => {
    const now = Date.now();
    fakePlatform.recordCycles('alfa', [
      aCompletedCycle(new Date(now - HOUR)),
      aCompletedCycle(new Date(now - 10 * 24 * HOUR)),
    ]);
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/decisions?period=7d' });

    expect(await rowsOf()).toHaveLength(1);
    expect(screen.getByText('1 decisione')).toBeInTheDocument();
  });

  it('says no decision falls in the period chosen', async () => {
    fakePlatform.recordCycles('alfa', decidedCycles());
    await renderApp({
      account: 'anna',
      url: '/flows/flow-alfa/decisions?period=range&from=2026-10-01T00:00Z&to=2026-10-02T00:00Z',
    });

    expect(await screen.findByText('Nessuna decisione nel periodo scelto.')).toBeInTheDocument();
  });

  it('waits for both ends of a range', async () => {
    await renderApp({
      account: 'anna',
      url: '/flows/flow-alfa/decisions?period=range&from=2026-11-14T08:07Z',
    });

    expect(
      await screen.findByText("Scegli l'inizio e la fine dell'intervallo."),
    ).toBeInTheDocument();
  });

  it('shows 50 decisions a page, with the next page', async () => {
    fakePlatform.recordCycles(
      'alfa',
      Array.from({ length: 60 }, (_, index) => aCompletedCycle(hoursBack(index))),
    );
    const user = userEvent.setup();
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/decisions' });

    expect(await rowsOf()).toHaveLength(50);
    await user.click(screen.getByRole('link', { name: 'Pagina successiva' }));

    await screen.findByText('Pagina 2');
    expect(await rowsOf()).toHaveLength(10);
    expect(screen.getByRole('link', { name: 'Pagina precedente' })).toHaveAttribute(
      'href',
      '/flows/flow-alfa/decisions',
    );
  });

  it('tells why the decisions could not be read', async () => {
    server.use(
      http.get('*/flows/:flowId/decisions', () =>
        HttpResponse.json({ detail: 'flusso non trovato' }, { status: 404 }),
      ),
    );
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/decisions' });

    expect(await screen.findByRole('alert')).toHaveTextContent('flusso non trovato');
  });
});
