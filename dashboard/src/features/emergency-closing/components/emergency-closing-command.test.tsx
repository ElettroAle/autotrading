import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { fakePlatform } from '@/testing/mocks/platform';
import { anOpenPosition } from '@/testing/mocks/positions';
import { problem } from '@/testing/mocks/responses';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

// ADR chiusura-di-emergenza-nella-dashboard: one command for the three scopes, on the page of the flow, on the page of
// the accounts and on the list of the flows, with the shared confirmation.
const COMMAND = 'Chiusura di emergenza';
const CONFIRMATION = 'Conferma della chiusura di emergenza';
const CONFIRM = 'Chiudi e metti in pausa';
const OUTCOME = 'Esito della chiusura di emergenza';

const click = async (name: string): Promise<void> => {
  await userEvent.click(await screen.findByRole('button', { name }));
};

const confirmation = async () => screen.findByRole('alertdialog', { name: CONFIRMATION });

const rowOf = async (name: string): Promise<HTMLElement> => {
  const rows = await screen.findAllByRole('row');
  const row = rows.find((candidate) => within(candidate).queryByText(name) !== null);
  if (row === undefined) {
    throw new Error(`no row with ${name}`);
  }
  return row;
};

const outcomeOf = (flows: object[]) =>
  http.post('*/flows/emergency-closings', () => HttpResponse.json({ flows }));

const anOutcome = (name: string, changes: object) => ({
  flow_id: `flow-${name}`,
  flow_name: name,
  closed: [],
  left_open: [],
  failure: null,
  remark: null,
  ...changes,
});

describe('the emergency closing', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addFlow('anna', 'alfa', { accountName: 'test-1', assets: ['BTC'] });
    fakePlatform.addFlow('anna', 'beta', { accountName: 'test-1', assets: ['ETH'] });
    fakePlatform.addFlow('anna', 'gamma', { accountName: 'test-2', assets: ['SOL'] });
    fakePlatform.holdPositions('alfa', [anOpenPosition({ asset: 'BTC' })]);
    fakePlatform.holdPositions('beta', [anOpenPosition({ asset: 'ETH' })]);
    fakePlatform.holdPositions('gamma', [anOpenPosition({ asset: 'SOL' })]);
  });

  it('of a flow asks to confirm with its name and its positions, closing nothing before', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    await click(COMMAND);

    expect(await confirmation()).toHaveTextContent(
      'Chiudere 1 posizione del flusso alfa e metterlo in pausa?',
    );
    expect(fakePlatform.emergencyClosings()).toBe(0);
    expect(fakePlatform.openPositionsOf('flow-alfa')).toHaveLength(1);
  });

  it('of a flow closes its positions once confirmed and shows the outcome of the flow', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });
    await click(COMMAND);
    await confirmation();

    await click(CONFIRM);

    expect(
      await screen.findByText('Chiusura di emergenza eseguita: i flussi sono in pausa.'),
    ).toBeInTheDocument();
    const outcome = await screen.findByRole('table', { name: OUTCOME });
    expect(within(outcome).getByRole('cell', { name: 'BTC' })).toBeInTheDocument();
    expect(fakePlatform.openPositionsOf('flow-alfa')).toHaveLength(0);
    expect(fakePlatform.flowNamed('alfa').status).toBe('in pausa');
    expect(fakePlatform.openPositionsOf('flow-gamma')).toHaveLength(1);
  });

  it('of an account names the account and the positions of its flows', async () => {
    await renderApp({ account: 'anna', url: '/accounts' });

    await userEvent.click(within(await rowOf('test-1')).getByRole('button', { name: COMMAND }));

    expect(await confirmation()).toHaveTextContent(
      'Chiudere 2 posizioni dei flussi del conto test-1 e metterli in pausa?',
    );
    expect(fakePlatform.emergencyClosings()).toBe(0);
  });

  it('of every flow names them all', async () => {
    await renderApp({ account: 'anna', url: '/' });

    await click(COMMAND);

    expect(await confirmation()).toHaveTextContent(
      'Chiudere 3 posizioni di tutti i flussi e metterli in pausa?',
    );
  });

  it('closes nothing when the user cancels', async () => {
    await renderApp({ account: 'anna', url: '/' });
    await click(COMMAND);
    await confirmation();

    await click('Annulla');

    expect(screen.queryByRole('alertdialog', { name: CONFIRMATION })).toBeNull();
    expect(await screen.findByRole('button', { name: COMMAND })).toBeEnabled();
    expect(fakePlatform.emergencyClosings()).toBe(0);
  });

  it('says which positions were not closed and why, and which flow had nothing to close', async () => {
    server.use(
      outcomeOf([
        anOutcome('alfa', { left_open: [{ asset: 'BTC', reason: 'Order rejected' }] }),
        anOutcome('beta', { failure: 'exchange non raggiungibile, riprovare' }),
        anOutcome('delta', { remark: 'nessuna posizione da chiudere' }),
      ]),
    );
    await renderApp({ account: 'anna', url: '/' });
    await click(COMMAND);
    await confirmation();

    await click(CONFIRM);

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Chiusura di emergenza incompleta: alcune posizioni non sono state chiuse. I flussi sono in pausa.',
    );
    const outcome = await screen.findByRole('table', { name: OUTCOME });
    expect(within(outcome).getByText('BTC: Order rejected')).toBeInTheDocument();
    expect(
      within(outcome).getByText('chiusura non riuscita: exchange non raggiungibile, riprovare'),
    ).toBeInTheDocument();
    expect(within(outcome).getByText('nessuna posizione da chiudere')).toBeInTheDocument();
  });

  it('shows the reason the API refuses the closing', async () => {
    server.use(
      http.post('*/flows/emergency-closings', () =>
        problem(503, 'Unavailable', 'exchange non raggiungibile'),
      ),
    );
    await renderApp({ account: 'anna', url: '/' });
    await click(COMMAND);
    await confirmation();

    await click(CONFIRM);

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Chiusura di emergenza non riuscita: exchange non raggiungibile',
    );
  });

  it('shows the reason the preview cannot be read, and lets the user go back', async () => {
    server.use(
      http.get('*/flows/emergency-closings/preview', () =>
        problem(503, 'Unavailable', 'exchange non raggiungibile, riprovare'),
      ),
    );
    await renderApp({ account: 'anna', url: '/' });
    await click(COMMAND);

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Chiusura di emergenza non disponibile: exchange non raggiungibile, riprovare',
    );
    await click('Annulla');
    expect(await screen.findByRole('button', { name: COMMAND })).toBeEnabled();
  });
});
