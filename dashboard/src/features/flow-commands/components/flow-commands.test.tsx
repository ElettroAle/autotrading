import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { delay, http, HttpResponse } from 'msw';

import {
  GO_COMMAND,
  HOLD_COMMAND,
  SECONDARY_COMMAND,
  STOP_COMMAND,
} from '@/components/ui/commands';
import { fakePlatform, type FakeFlow } from '@/testing/mocks/platform';
import { anOpenPosition } from '@/testing/mocks/positions';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const FLOW_PAGE = '/flows/flow-alfa';
const STOP_CONFIRMATION = 'Conferma dello stop';
const RUN_NOW = 'Esegui ora';
const CYCLE_IN_PROGRESS = 'un ciclo del flusso è già in corso';

const commands = () => screen.getByRole('group', { name: 'Comandi del flusso' });

const offeredCommands = async (): Promise<string[]> => {
  await screen.findByRole('group', { name: 'Comandi del flusso' });
  return within(commands())
    .queryAllByRole('button')
    .map((button) => button.textContent ?? '');
};

const click = async (name: string): Promise<void> => {
  await userEvent.click(await screen.findByRole('button', { name }));
};

describe('FlowCommands', () => {
  let alfa: FakeFlow;

  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    alfa = fakePlatform.addFlow('anna', 'alfa');
  });

  it.each([
    ['attivo', ['Pausa', 'Stop', RUN_NOW]],
    ['in pausa', ['Riprendi', 'Stop']],
    // Archivia is in the settings of the flow, not among the commands of every day (Bug 560).
    ['fermo', ['Avvia']],
  ])('offers for a flow %s only the commands its status admits', async (status, expected) => {
    alfa.status = status;
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    expect(await offeredCommands()).toEqual(expected);
  });

  it.each([
    ['fermo', 'Avvia', GO_COMMAND],
    ['in pausa', 'Riprendi', GO_COMMAND],
    ['attivo', 'Pausa', HOLD_COMMAND],
    ['attivo', 'Stop', STOP_COMMAND],
    ['attivo', RUN_NOW, SECONDARY_COMMAND],
  ])('for a flow %s shows %s with the look of its weight', async (status, name, look) => {
    alfa.status = status;
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    expect(
      await within(await screen.findByRole('group', { name: 'Comandi del flusso' })).findByRole(
        'button',
        { name },
      ),
    ).toHaveAttribute('class', look);
  });

  it.each([
    ['fermo', 'Avvia', 'play'],
    ['in pausa', 'Riprendi', 'play'],
    ['attivo', 'Pausa', 'pause'],
    ['attivo', 'Stop', 'square'],
  ])(
    'for a flow %s shows %s with its icon, named by its text alone',
    async (status, name, icon) => {
      alfa.status = status;
      await renderApp({ account: 'anna', url: FLOW_PAGE });

      const button = await within(
        await screen.findByRole('group', { name: 'Comandi del flusso' }),
      ).findByRole('button', { name });
      expect(button).toHaveAccessibleName(name);
      expect(within(button).getByRole('img', { hidden: true })).toHaveAttribute('data-icon', icon);
    },
  );

  it('pauses the flow and then offers to resume it', async () => {
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    await click('Pausa');

    expect(await screen.findByText('Stato: in pausa')).toBeInTheDocument();
    expect(fakePlatform.flowNamed('alfa').status).toBe('in pausa');
    expect(await offeredCommands()).toEqual(['Riprendi', 'Stop']);
  });

  it('resumes a paused flow', async () => {
    alfa.status = 'in pausa';
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    await click('Riprendi');

    expect(await screen.findByText('Stato: attivo')).toBeInTheDocument();
    expect(fakePlatform.flowNamed('alfa').status).toBe('attivo');
  });

  it('keeps every command disabled while one is under way', async () => {
    server.use(
      http.post('*/flows/:flowId/:command', async () => {
        await delay('infinite');
        return new HttpResponse(null, { status: 204 });
      }),
    );
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    await click('Pausa');

    expect(screen.getByRole('button', { name: 'Pausa' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Stop' })).toBeDisabled();
  });

  it('asks to confirm the stop, saying which open positions it will close', async () => {
    fakePlatform.holdPositions('alfa', [
      anOpenPosition({ asset: 'BTC' }),
      anOpenPosition({ asset: 'ETH' }),
    ]);
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    await click('Stop');

    const confirmation = await screen.findByRole('alertdialog', { name: STOP_CONFIRMATION });
    expect(await within(confirmation).findByText('La posizione su BTC sarà chiusa')).toBeVisible();
    expect(within(confirmation).getByText('La posizione su ETH sarà chiusa')).toBeVisible();
    expect(fakePlatform.flowNamed('alfa').status).toBe('attivo');
  });

  it('starts a stopped flow on the test network without asking', async () => {
    alfa.status = 'fermo';
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    await click('Avvia');

    expect(await screen.findByText('Stato: attivo')).toBeInTheDocument();
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  });

  it('starts a stopped flow on real money only once the user confirms it', async () => {
    fakePlatform.configureExchangeNetwork('real');
    alfa.status = 'fermo';
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    await click('Avvia');
    expect(
      await screen.findByRole('alertdialog', { name: "Conferma dell'avvio" }),
    ).toHaveTextContent('Il flusso opererà con denaro reale');
    expect(fakePlatform.flowNamed('alfa').status).toBe('fermo');
    await click('Avvia con denaro reale');

    expect(await screen.findByText('Stato: attivo')).toBeInTheDocument();
  });

  it('stops the flow once the user confirms, closing its positions', async () => {
    fakePlatform.holdPositions('alfa', [anOpenPosition({ asset: 'BTC' })]);
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    await click('Stop');
    await click('Conferma lo stop');

    expect(await screen.findByText('Stato: fermo')).toBeInTheDocument();
    expect(fakePlatform.openPositionsOf(alfa.id)).toEqual([]);
    expect(screen.queryByRole('alertdialog', { name: STOP_CONFIRMATION })).toBeNull();
    expect(await offeredCommands()).toEqual(['Avvia']);
  });

  it('says the stop closes nothing when the flow has no open position', async () => {
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    await click('Stop');

    expect(
      await within(screen.getByRole('alertdialog', { name: STOP_CONFIRMATION })).findByText(
        'Il flusso non ha posizioni aperte.',
      ),
    ).toBeVisible();
  });

  it('says every open position will be closed when their list cannot be read', async () => {
    server.use(
      http.get('*/flows/:flowId/state', () =>
        HttpResponse.json({ detail: 'exchange non raggiungibile' }, { status: 503 }),
      ),
    );
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    await click('Stop');

    const confirmation = screen.getByRole('alertdialog', { name: STOP_CONFIRMATION });
    expect(await within(confirmation).findByRole('alert')).toHaveTextContent(
      'Impossibile leggere i dati: exchange non raggiungibile',
    );
    expect(
      within(confirmation).getByText('Tutte le posizioni aperte del flusso saranno chiuse.'),
    ).toBeVisible();
  });

  it('keeps the flow running when the user cancels the stop', async () => {
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    await click('Stop');
    await click('Annulla');

    expect(screen.queryByRole('alertdialog', { name: STOP_CONFIRMATION })).toBeNull();
    expect(await offeredCommands()).toEqual(['Pausa', 'Stop', RUN_NOW]);
    expect(fakePlatform.flowNamed('alfa').status).toBe('attivo');
  });

  it('shows the reason the API gives for a command it refuses', async () => {
    alfa.status = 'fermo';
    fakePlatform.addFlow('anna', 'beta', { assets: ['ETH'], allocatedCapital: 950 });
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    await click('Avvia');

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Comando non riuscito: capitale allocato oltre il capitale libero: 50 USDC',
    );
    expect(screen.getByText('Stato: fermo')).toBeInTheDocument();
  });

  it('shows the reason of a refused stop and closes the confirmation', async () => {
    server.use(
      http.post('*/flows/:flowId/stop', () =>
        HttpResponse.json(
          { detail: 'comando ferma non ammesso per un flusso fermo' },
          { status: 409 },
        ),
      ),
    );
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    await click('Stop');
    await click('Conferma lo stop');

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Comando non riuscito: comando ferma non ammesso per un flusso fermo',
    );
    expect(screen.queryByRole('alertdialog', { name: STOP_CONFIRMATION })).toBeNull();
  });

  // R6.5.2, ADR pulsante-esegui-ora-nella-pagina-del-flusso.
  describe('Esegui ora', () => {
    it('runs a cycle of the active flow now, without asking, and says how it ended', async () => {
      await renderApp({ account: 'anna', url: FLOW_PAGE });

      await click(RUN_NOW);

      expect(await screen.findByRole('status')).toHaveTextContent('Ciclo eseguito: concluso.');
      expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
      expect(fakePlatform.cyclesOf(alfa.id).map((cycle) => cycle.trigger)).toEqual(['on_demand']);
    });

    it('waits for the cycle with the command disabled, saying a cycle is under way', async () => {
      server.use(
        http.post('*/flows/:flowId/cycles', async () => {
          await delay('infinite');
          return new HttpResponse(null, { status: 201 });
        }),
      );
      await renderApp({ account: 'anna', url: FLOW_PAGE });

      await click(RUN_NOW);

      expect(await screen.findByRole('button', { name: 'Ciclo in corso…' })).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Pausa' })).toBeDisabled();
      expect(screen.queryByRole('button', { name: RUN_NOW })).toBeNull();
    });

    it('shows the reason the API gives when a cycle of the flow is already under way', async () => {
      fakePlatform.holdCycle('alfa');
      await renderApp({ account: 'anna', url: FLOW_PAGE });

      await click(RUN_NOW);

      expect(await screen.findByRole('alert')).toHaveTextContent(
        `Ciclo rifiutato: ${CYCLE_IN_PROGRESS}`,
      );
      expect(fakePlatform.cyclesOf(alfa.id)).toEqual([]);
      expect(screen.getByRole('button', { name: RUN_NOW })).toBeEnabled();
    });

    it('reads the cycles of the flow again, showing the new one as asked for', async () => {
      await renderApp({ account: 'anna', url: `${FLOW_PAGE}/cycles` });
      expect(await screen.findByText('Nessun ciclo registrato.')).toBeInTheDocument();

      await click(RUN_NOW);

      const rows = within(await screen.findByRole('table', { name: 'Cicli' })).getAllByRole('row');
      expect(rows.at(-1)).toHaveTextContent('su richiesta');
    });

    // Bug 574, ADR-chiavi-delle-letture-del-flusso-con-l-id: the curve is read again once the cycle ends.
    it('reads the equity curve of the flow again, drawing the point of the new cycle', async () => {
      fakePlatform.recordEquity('alfa', new Date(Date.now() - 60 * 60_000), 300);
      // The cycle records its equity as the worker does; returning nothing lets the platform answer.
      server.use(
        http.post('*/flows/:flowId/cycles', () => {
          fakePlatform.recordEquity('alfa', new Date(), 310);
        }),
      );
      await renderApp({ account: 'anna', url: FLOW_PAGE });
      const curve = await screen.findByRole('figure', { name: 'Equity curve' });
      expect(within(curve).getAllByRole('img', { name: /^Equity / })).toHaveLength(1);

      await click(RUN_NOW);

      await expect
        .poll(() => within(curve).queryAllByRole('img', { name: /^Equity / }))
        .toHaveLength(2);
    });
  });
});
