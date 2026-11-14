import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import {
  aCompletedCycle,
  aFailedCycle,
  reasoningOf,
  STEPS,
  type FakeCycle,
} from '@/testing/mocks/cycles';
import { fakePlatform } from '@/testing/mocks/platform';
import { renderApp } from '@/testing/test-utils';

const PLANNED_AT = new Date('2026-11-14T09:07:00Z');
const URL_OF_CYCLE = '/flows/flow-alfa/cycles/2026-11-14T09%3A07%3A00Z';

const section = (title: string) => screen.findByRole('group', { name: title });

const openCycle = async (cycle: FakeCycle) => {
  fakePlatform.recordCycles('alfa', [cycle]);
  return renderApp({ account: 'anna', url: URL_OF_CYCLE });
};

const withDocument = (
  cycle: FakeCycle,
  step: string,
  content: Record<string, unknown>,
): FakeCycle => ({
  ...cycle,
  documents: cycle.documents.map((document) =>
    document.step === step ? { step, content } : document,
  ),
});

describe('CycleView', () => {
  beforeEach(() => {
    fakePlatform.giveFlowTo('anna', 'alfa');
  });

  it('sums up the cycle: instants, outcome, cost and the steps it ran', async () => {
    await openCycle(aCompletedCycle(PLANNED_AT));

    const summary = await screen.findByRole('region', { name: 'Riepilogo del ciclo' });
    expect(summary).toHaveTextContent('Pianificato14/11/2026, 10:07:00');
    expect(summary).toHaveTextContent('Avviato14/11/2026, 10:07:02 (2 s di ritardo)');
    expect(summary).toHaveTextContent('Esitoconcluso');
    expect(summary).toHaveTextContent(
      'Costo del modello0.0125 USD (1200 token in ingresso, 300 in uscita)',
    );
    const steps = screen.getByRole('list', { name: 'Passi eseguiti' });
    expect(within(steps).getAllByRole('listitem')).toHaveLength(8);
  });

  it('shows each decision with its full reasoning, and the raw answer of the agent', async () => {
    await openCycle(aCompletedCycle(PLANNED_AT));

    const decisions = await section('Decisioni e ragionamento');
    expect(within(decisions).getByRole('heading', { name: 'apri long BTC' })).toBeInTheDocument();
    expect(within(decisions).getByText(reasoningOf('BTC'))).toBeInTheDocument();
    expect(await section("Risposta integrale dell'agente")).toHaveTextContent('"action": "open"');
  });

  it('shows the discarded decisions and the assets the agent left out', async () => {
    const cycle = aCompletedCycle(PLANNED_AT);
    await openCycle(
      withDocument(cycle, STEPS.agentDecision, {
        risposta: '{}',
        decisioni: [],
        scartate: [{ tipo: 'DiscardedDecision', asset: 'SOL', reason: 'leva assente' }],
        mancanti: ['ETH'],
      }),
    );

    const decisions = await section('Decisioni e ragionamento');
    expect(decisions).toHaveTextContent('Nessuna decisione valida.');
    expect(decisions).toHaveTextContent('leva assente');
    expect(decisions).toHaveTextContent('Asset senza decisione: ETH');
  });

  it('shows the context sent to the agent, message by message', async () => {
    await openCycle(aCompletedCycle(PLANNED_AT));

    const context = await section('Contesto inviato');
    expect(within(context).getByRole('heading', { name: 'system' })).toBeInTheDocument();
    expect(context).toHaveTextContent('Sei il gestore del flusso alfa.');
  });

  it('shows the data of each source, the risk check, the orders and the flow', async () => {
    await openCycle(aCompletedCycle(PLANNED_AT));

    const sources = await section('Dati delle fonti');
    expect(within(sources).getByRole('heading', { name: 'indicatori' })).toBeInTheDocument();
    expect(within(sources).getByRole('heading', { name: 'forecast' })).toBeInTheDocument();
    expect(sources).toHaveTextContent('"prezzo_tra_1h": "97250.5"');
    expect(await section('Controllo del rischio')).toHaveTextContent('"tipo": "ApprovedOpening"');
    expect(await section('Esecuzione degli ordini')).toHaveTextContent('"coin": "BTC"');
    expect(await section("Flusso all'avvio")).toHaveTextContent('"modello": "openai/gpt-4o"');
    expect(await section('Flusso alla fine')).toHaveTextContent('"tipo": "FlowStateView"');
  });

  it('names the sources that gave no data, with the reason', async () => {
    await openCycle({
      ...aCompletedCycle(PLANNED_AT),
      absent_sources: [{ source: 'notizie', reason: 'nessuna risposta entro 30 secondi' }],
    });

    expect(await section('Fonti assenti')).toHaveTextContent(
      'notizie: nessuna risposta entro 30 secondi',
    );
  });

  it('never reads the texts of the model as HTML (ADR 0129)', async () => {
    const cycle = aCompletedCycle(PLANNED_AT);
    await openCycle(
      withDocument(cycle, STEPS.composeContext, {
        messaggi: [{ ruolo: 'user', contenuto: '<img src=x onerror="alert(1)"><b>grassetto</b>' }],
      }),
    );

    const context = await section('Contesto inviato');
    expect(context).toHaveTextContent('<img src=x onerror="alert(1)"><b>grassetto</b>');
    expect(within(context).queryByRole('img')).not.toBeInTheDocument();
  });

  it('shows a document of another shape, or of a step it does not know, as it is', async () => {
    const changed = [
      [STEPS.collectSources, { fonti: 'nessuna' }],
      [STEPS.composeContext, { testo: 'contesto libero' }],
      [STEPS.agentDecision, { risposta: 42 }],
    ] as const;
    const cycle = changed.reduce(
      (each, [step, content]) => withDocument(each, step, content),
      aCompletedCycle(PLANNED_AT),
    );
    await openCycle({
      ...cycle,
      documents: [...cycle.documents, { step: 'passo nuovo', content: { valore: 1 } }],
    });

    expect(await section('Dati delle fonti')).toHaveTextContent('"fonti": "nessuna"');
    expect(await section('Contesto inviato')).toHaveTextContent('"testo": "contesto libero"');
    expect(await section('Decisioni e ragionamento')).toHaveTextContent('"risposta": 42');
    expect(await section('passo nuovo')).toHaveTextContent('"valore": 1');
  });

  it('lets the user close and reopen a section', async () => {
    const user = userEvent.setup();
    await openCycle(aCompletedCycle(PLANNED_AT));

    const context = await section('Contesto inviato');
    expect(context).toHaveAttribute('open');
    await user.click(within(context).getByText('Contesto inviato'));
    expect(context).not.toHaveAttribute('open');
  });

  it('shows where a failed cycle stopped, why, and what it produced before', async () => {
    await openCycle(
      aFailedCycle(aCompletedCycle(PLANNED_AT), STEPS.agentDecision, {
        errorType: 'ModelCallTimeoutError',
        message: 'il modello non ha risposto entro 60 secondi',
      }),
    );

    const failure = await screen.findByRole('region', { name: 'Errore del ciclo' });
    expect(failure).toHaveTextContent("Passodecisione dell'agente");
    expect(failure).toHaveTextContent('TipoModelCallTimeoutError');
    expect(failure).toHaveTextContent('Motivoil modello non ha risposto entro 60 secondi');
    expect(screen.getByRole('region', { name: 'Riepilogo del ciclo' })).toHaveTextContent(
      'Costo del modellonon disponibile',
    );
    expect(await section('Contesto inviato')).toBeInTheDocument();
    expect(
      screen.queryByRole('group', { name: 'Decisioni e ragionamento' }),
    ).not.toBeInTheDocument();
  });

  it('says a skipped cycle never started', async () => {
    await openCycle({
      ...aCompletedCycle(PLANNED_AT),
      outcome: 'saltato',
      started_at: null,
      delay_seconds: null,
      steps: [],
      documents: [],
      cost: null,
    });

    const summary = await screen.findByRole('region', { name: 'Riepilogo del ciclo' });
    expect(summary).toHaveTextContent('Avviatomai');
    expect(screen.queryByRole('list', { name: 'Passi eseguiti' })).not.toBeInTheDocument();
  });

  it('shows the start alone when the delay is not recorded', async () => {
    await openCycle({ ...aCompletedCycle(PLANNED_AT), delay_seconds: null });

    const summary = await screen.findByRole('region', { name: 'Riepilogo del ciclo' });
    expect(summary).toHaveTextContent('Avviato14/11/2026, 10:07:02Esito');
  });

  it('says a cost the provider did not give is unknown', async () => {
    await openCycle({
      ...aCompletedCycle(PLANNED_AT),
      cost: { input_tokens: 10, output_tokens: 5, cost_usd: null },
    });

    expect(await screen.findByRole('region', { name: 'Riepilogo del ciclo' })).toHaveTextContent(
      'Costo del modellosconosciuto (10 token in ingresso, 5 in uscita)',
    );
  });

  it('leads back to the cycles of the flow', async () => {
    await openCycle(aCompletedCycle(PLANNED_AT));

    expect(await screen.findByRole('link', { name: 'Tutti i cicli del flusso' })).toHaveAttribute(
      'href',
      '/flows/flow-alfa/cycles',
    );
  });

  it('tells why the cycle could not be read', async () => {
    await renderApp({ account: 'anna', url: URL_OF_CYCLE });

    expect(await screen.findByRole('alert')).toHaveTextContent('ciclo non trovato');
  });
});
