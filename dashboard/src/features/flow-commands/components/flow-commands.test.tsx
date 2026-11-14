import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { delay, http, HttpResponse } from 'msw';

import { fakePlatform, type FakeFlow } from '@/testing/mocks/platform';
import { anOpenPosition } from '@/testing/mocks/positions';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const FLOW_PAGE = '/flows/flow-alfa';
const STOP_CONFIRMATION = 'Conferma dello stop';
const ARCHIVE_CONFIRMATION = "Conferma dell'archiviazione";

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
    ['attivo', ['Pausa', 'Stop']],
    ['in pausa', ['Riprendi', 'Stop']],
    ['fermo', ['Avvia', 'Archivia']],
  ])('offers for a flow %s only the commands its status admits', async (status, expected) => {
    alfa.status = status;
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    expect(await offeredCommands()).toEqual(expected);
  });

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

  it('stops the flow once the user confirms, closing its positions', async () => {
    fakePlatform.holdPositions('alfa', [anOpenPosition({ asset: 'BTC' })]);
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    await click('Stop');
    await click('Conferma lo stop');

    expect(await screen.findByText('Stato: fermo')).toBeInTheDocument();
    expect(fakePlatform.openPositionsOf(alfa.id)).toEqual([]);
    expect(screen.queryByRole('alertdialog', { name: STOP_CONFIRMATION })).toBeNull();
    expect(await offeredCommands()).toEqual(['Avvia', 'Archivia']);
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
    expect(await offeredCommands()).toEqual(['Pausa', 'Stop']);
    expect(fakePlatform.flowNamed('alfa').status).toBe('attivo');
  });

  it('asks to confirm the archiving, saying it is final and leaves no position to manage', async () => {
    alfa.status = 'fermo';
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    await click('Archivia');

    expect(screen.getByRole('alertdialog', { name: ARCHIVE_CONFIRMATION })).toHaveTextContent(
      "L'archiviazione è definitiva: il flusso non si potrà più avviare né modificare. Un flusso fermo non ha posizioni aperte da gestire e il suo capitale allocato torna libero sul conto.",
    );
    expect(fakePlatform.flowNamed('alfa').status).toBe('fermo');
  });

  it('archives the flow once the user confirms and goes back to the flows in use', async () => {
    alfa.status = 'fermo';
    fakePlatform.addFlow('anna', 'beta');
    const { router } = await renderApp({ account: 'anna', url: FLOW_PAGE });

    await click('Archivia');
    await click("Conferma l'archiviazione");

    expect(await screen.findByRole('link', { name: 'beta' })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/');
    expect(screen.queryByRole('link', { name: 'alfa' })).toBeNull();
    expect(fakePlatform.flowNamed('alfa').status).toBe('archiviato');
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
});
