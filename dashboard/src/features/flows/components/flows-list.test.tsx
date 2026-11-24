import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { aCompletedCycle, aFailedCycle, STEPS } from '@/testing/mocks/cycles';
import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const LAST_CYCLE = new Date('2026-11-14T10:07:00+01:00');
const MINUTE = 60_000;
const DAY = 24 * 60 * MINUTE;

const summaryOf = async (name: string) => screen.findByRole('article', { name });

const factOf = (summary: HTMLElement, term: string) => within(summary).getByLabelText(term);

describe('FlowsList', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addUser('bruno', { hasUserRole: true });
    fakePlatform.addFlow('bruno', 'omega');
  });

  it('lists the flows of the tenant of the user, each leading to its page', async () => {
    fakePlatform.addFlow('anna', 'alfa');
    await renderApp({ account: 'anna' });

    const flows = await screen.findByRole('list', { name: 'Flussi' });
    expect(within(flows).getByRole('link', { name: 'alfa' })).toHaveAttribute(
      'href',
      '/flows/flow-alfa',
    );
    expect(within(flows).getByText('attivo')).toBeInTheDocument();
    expect(within(flows).getByLabelText('Versione')).toHaveTextContent('1');
    expect(screen.queryByText('omega')).not.toBeInTheDocument();
  });

  // Bug 572: the boxes of the flows stuck together. Each box is the shared card, white on the page (Bug 726).
  it('ADR-riquadri-dei-flussi-separati: shows each flow in a separate box, spaced from the others', async () => {
    fakePlatform.addFlow('anna', 'alfa');
    fakePlatform.addFlow('anna', 'beta');
    await renderApp({ account: 'anna' });

    const flows = await screen.findByRole('list', { name: 'Flussi' });
    expect(flows).toHaveClass('space-y-3');
    expect(flows).not.toHaveClass('divide-y');
    expect(flows).not.toHaveClass('border');
    const boxes = within(flows).getAllByRole('listitem');
    expect(boxes).toHaveLength(2);
    boxes.forEach((box) =>
      expect(box).toHaveClass('rounded-lg', 'border', 'border-slate-200', 'bg-white', 'p-4'),
    );
  });

  it('shows where an active flow runs, its last and next cycle and a gain in green', async () => {
    fakePlatform.addFlow('anna', 'alfa');
    fakePlatform.changeFlow('alfa', { allocatedCapital: 300, currentCapital: 330 });
    const last = aCompletedCycle(LAST_CYCLE);
    const failed = aFailedCycle(
      aCompletedCycle(new Date(LAST_CYCLE.getTime() - 15 * MINUTE)),
      STEPS.agentDecision,
      { errorType: 'ModelCallTimeoutError', message: 'nessuna risposta' },
    );
    const skipped = {
      ...aCompletedCycle(new Date(LAST_CYCLE.getTime() - 30 * MINUTE)),
      outcome: 'saltato',
    };
    fakePlatform.recordCycles('alfa', [skipped, failed, last]);
    await renderApp({ account: 'anna' });

    const alfa = await summaryOf('alfa');
    expect(factOf(alfa, 'Stato')).toHaveTextContent('attivo');
    expect(factOf(alfa, 'Conto')).toHaveTextContent('principale');
    expect(factOf(alfa, 'Modello')).toHaveTextContent('openai/gpt-4o');
    expect(factOf(alfa, 'Ultima esecuzione')).toHaveTextContent('14/11/2026, 10:07:00 · concluso');
    expect(factOf(alfa, 'Prossima esecuzione prevista')).toHaveTextContent('14/11/2026, 10:22:00');
    expect(factOf(alfa, 'Capitale iniziale')).toHaveTextContent('300 USDC');
    expect(factOf(alfa, 'Capitale attuale')).toHaveTextContent('330 USDC');
    expect(factOf(alfa, 'Rendimento')).toHaveTextContent('+10,00%');
    expect(factOf(alfa, 'Rendimento')).toHaveClass('text-green-700');
    expect(within(alfa).queryByLabelText('Motivo della pausa')).not.toBeInTheDocument();
  });

  // R6.4.2, ADR riepilogo-dei-risultati-nella-dashboard: the summary replaces the row of the outcomes and the
  // environment, which the header already says.
  it('shows the summary of the results of each flow instead of its outcomes and its environment', async () => {
    fakePlatform.addFlow('anna', 'alfa');
    fakePlatform.changeFlow('alfa', { allocatedCapital: 100, currentCapital: 102.5 });
    fakePlatform.recordCycles('alfa', [aCompletedCycle(LAST_CYCLE)]);
    await renderApp({ account: 'anna' });

    const alfa = await summaryOf('alfa');
    const results = within(alfa).getByRole('region', { name: 'Riepilogo dei risultati' });
    expect(within(results).getByLabelText('Guadagno attuale')).toHaveTextContent(
      '+2,50 USDC · +2,50%',
    );
    expect(within(alfa).queryByLabelText('Ambiente')).not.toBeInTheDocument();
    expect(
      within(alfa).queryByRole('list', { name: 'Esito degli ultimi cicli' }),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole('list', { name: 'Legenda degli esiti' })).not.toBeInTheDocument();
  });

  it('measures the results in the period chosen above the list', async () => {
    fakePlatform.addFlow('anna', 'alfa');
    const now = Date.now();
    fakePlatform.recordEquity('alfa', new Date(now - 10 * DAY), 100);
    fakePlatform.recordEquity('alfa', new Date(now - 5 * DAY), 101);
    fakePlatform.recordEquity('alfa', new Date(now - DAY), 101.5);
    await renderApp({ account: 'anna', url: '/?period=7d' });

    const results = within(await summaryOf('alfa')).getByRole('region', {
      name: 'Riepilogo dei risultati',
    });
    expect(within(results).getByLabelText('Guadagno nel periodo')).toHaveTextContent(
      '+0,50 USDC · +0,50%',
    );
  });

  it('shows no summary for a draft, which has no account yet', async () => {
    fakePlatform.addFlow('anna', 'bozza', { status: 'bozza', allocatedCapital: null });
    fakePlatform.changeFlow('bozza', { accountId: null });
    await renderApp({ account: 'anna' });

    const draft = await summaryOf('bozza');
    expect(
      within(draft).queryByRole('region', { name: 'Riepilogo dei risultati' }),
    ).not.toBeInTheDocument();
  });

  // Bug 731, ADR asset-del-flusso-nel-riepilogo-dei-flussi.
  it('shows the assets of a flow in the order of its configuration', async () => {
    fakePlatform.addFlow('anna', 'alfa');
    fakePlatform.changeFlow('alfa', { assets: ['ETH', 'SOL', 'BTC'] });
    await renderApp({ account: 'anna' });

    expect(factOf(await summaryOf('alfa'), 'Asset')).toHaveTextContent('ETH · SOL · BTC');
  });

  it('shows no asset for a draft without assets', async () => {
    fakePlatform.addFlow('anna', 'bozza', { status: 'bozza', allocatedCapital: null });
    fakePlatform.changeFlow('bozza', { accountId: null, assets: [] });
    await renderApp({ account: 'anna' });

    expect(factOf(await summaryOf('bozza'), 'Asset')).toHaveTextContent('nessuno');
  });

  it('shows why a flow paused, a loss in red and no next cycle', async () => {
    fakePlatform.addFlow('anna', 'beta');
    fakePlatform.changeFlow('beta', {
      status: 'in pausa',
      pauseReason: 'chiave del fornitore non valida',
      allocatedCapital: 300,
      currentCapital: 270,
    });
    await renderApp({ account: 'anna' });

    const beta = await summaryOf('beta');
    expect(factOf(beta, 'Stato')).toHaveTextContent('in pausa');
    expect(factOf(beta, 'Motivo della pausa')).toHaveTextContent('chiave del fornitore non valida');
    expect(factOf(beta, 'Ultima esecuzione')).toHaveTextContent('nessuna');
    expect(within(beta).queryByLabelText('Prossima esecuzione prevista')).not.toBeInTheDocument();
    expect(factOf(beta, 'Rendimento')).toHaveTextContent('-10,00%');
    expect(factOf(beta, 'Rendimento')).toHaveClass('text-red-700');
  });

  // ADR perdita-massima-nella-dashboard: the same notice as the page of the flow, beside the status.
  it('shows beside the status that the openings of a flow are suspended, and why', async () => {
    fakePlatform.addFlow('anna', 'alfa');
    fakePlatform.addFlow('anna', 'beta');
    fakePlatform.changeFlow('alfa', {
      openingsSuspension: {
        reason: 'perdita giornaliera 6% oltre il 5%',
        suspendedAt: '2026-11-14T09:00:00Z',
      },
    });
    await renderApp({ account: 'anna' });

    const alfa = await summaryOf('alfa');
    expect(within(alfa).getByRole('status')).toHaveTextContent(
      'aperture sospese: perdita giornaliera 6% oltre il 5%',
    );
    expect(within(await summaryOf('beta')).queryByRole('status')).not.toBeInTheDocument();
  });

  it('shows a return the API could not measure without a colour', async () => {
    fakePlatform.addFlow('anna', 'gamma');
    fakePlatform.changeFlow('gamma', { allocatedCapital: 0, currentCapital: 0 });
    await renderApp({ account: 'anna' });

    const gamma = await summaryOf('gamma');
    expect(factOf(gamma, 'Rendimento')).toHaveTextContent('non disponibile');
    expect(factOf(gamma, 'Rendimento')).toHaveClass('text-slate-700');
  });

  it('shows a draft without account capital, which it does not have yet', async () => {
    fakePlatform.addFlow('anna', 'bozza', { status: 'bozza', allocatedCapital: null });
    fakePlatform.changeFlow('bozza', { accountId: null });
    await renderApp({ account: 'anna' });

    const draft = await summaryOf('bozza');
    expect(factOf(draft, 'Capitale iniziale')).toHaveTextContent('non disponibile');
    expect(factOf(draft, 'Rendimento')).toHaveTextContent('non disponibile');
  });

  it('leaves the archived flows out', async () => {
    fakePlatform.addFlow('anna', 'delta');
    fakePlatform.changeFlow('delta', { status: 'archiviato' });
    await renderApp({ account: 'anna' });

    expect(await screen.findByText('Non hai ancora flussi.')).toBeInTheDocument();
  });

  it('says the user has no flow yet', async () => {
    await renderApp({ account: 'anna' });

    expect(await screen.findByText('Non hai ancora flussi.')).toBeInTheDocument();
  });

  it('tells why the flows could not be read', async () => {
    server.use(
      http.get('*/flows/overview', () =>
        HttpResponse.json({ detail: 'exchange non raggiungibile, riprovare' }, { status: 503 }),
      ),
    );
    await renderApp({ account: 'anna' });

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'exchange non raggiungibile, riprovare',
    );
  });

  it('keeps showing the flows when a rereading fails', async () => {
    fakePlatform.addFlow('anna', 'alfa');
    await renderApp({ account: 'anna' });
    await screen.findByRole('list', { name: 'Flussi' });
    fakePlatform.stopApi();

    await userEvent.click(screen.getByRole('button', { name: 'Aggiorna' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Dati non aggiornati');
    expect(screen.getByRole('link', { name: 'alfa' })).toBeInTheDocument();
  });
});
