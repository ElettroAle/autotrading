import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';

import { aCompletedCycle, aFailedCycle, STEPS } from '@/testing/mocks/cycles';
import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const LAST_CYCLE = new Date('2026-11-14T10:07:00+01:00');
const MINUTE = 60_000;

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
    expect(screen.queryByText('omega')).not.toBeInTheDocument();
  });

  it('shows where an active flow runs, its cycles and a gain in green', async () => {
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
    expect(factOf(alfa, 'Ambiente')).toHaveTextContent('dev');
    expect(factOf(alfa, 'Modello')).toHaveTextContent('openai/gpt-4o');
    expect(factOf(alfa, 'Ultima esecuzione')).toHaveTextContent('14/11/2026, 10:07:00 · concluso');
    expect(factOf(alfa, 'Prossima esecuzione prevista')).toHaveTextContent('14/11/2026, 10:22:00');
    expect(factOf(alfa, 'Capitale iniziale')).toHaveTextContent('300 USDC');
    expect(factOf(alfa, 'Capitale attuale')).toHaveTextContent('330 USDC');
    expect(factOf(alfa, 'Rendimento')).toHaveTextContent('+10,00%');
    expect(factOf(alfa, 'Rendimento')).toHaveClass('text-green-700');
    expect(within(alfa).queryByLabelText('Motivo della pausa')).not.toBeInTheDocument();
    const outcomes = within(
      within(alfa).getByRole('list', { name: 'Esito degli ultimi cicli' }),
    ).getAllByRole('listitem');
    expect(outcomes.map((outcome) => outcome.textContent)).toEqual([
      '✓concluso, 10:07:00',
      '✗fallito, 09:52:00',
      '–saltato, 09:37:00',
    ]);
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
    expect(within(beta).getByText('Nessun ciclo registrato.')).toBeInTheDocument();
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
});
