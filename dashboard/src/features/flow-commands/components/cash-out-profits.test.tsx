import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { fakePlatform } from '@/testing/mocks/platform';
import { anOpenPosition } from '@/testing/mocks/positions';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

// ADR incasso-dei-profitti-nella-dashboard: the cash-out among the commands of the flow, with the shared confirmation.
const FLOW_PAGE = '/flows/flow-alfa';
const CASH_OUT = 'Incassa i profitti';
const CONFIRMATION = "Conferma dell'incasso";

const commands = async () => screen.findByRole('group', { name: 'Comandi del flusso' });

const click = async (name: string): Promise<void> => {
  await userEvent.click(await screen.findByRole('button', { name }));
};

const confirmation = async () => screen.findByRole('alertdialog', { name: CONFIRMATION });

describe('the cash-out of the profits of a flow', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addFlow('anna', 'alfa', { allocatedCapital: 500, currentCapital: 620 });
    fakePlatform.holdPositions('alfa', [anOpenPosition({ asset: 'BTC' })]);
  });

  it('is offered on a flow worth more than its capital', async () => {
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    expect(await within(await commands()).findByRole('button', { name: CASH_OUT })).toBeEnabled();
  });

  it.each([460, 500])('is not offered on a flow worth %s on a capital of 500', async (value) => {
    fakePlatform.changeFlow('alfa', { currentCapital: value });
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    // The confirmation of the stop lists the positions of the same reading: once shown, the state has been read.
    await click('Stop');
    expect(await screen.findByText('La posizione su BTC sarà chiusa')).toBeInTheDocument();
    await click('Annulla');

    expect(within(await commands()).queryByRole('button', { name: CASH_OUT })).toBeNull();
  });

  it('asks to confirm with the estimate at the value of now and closes nothing before', async () => {
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    await click(CASH_OUT);

    expect(await confirmation()).toHaveTextContent(
      'Chiudere 1 posizione di alfa e liberare circa 120 USDC?',
    );
    expect(fakePlatform.cashOutsOf('alfa')).toBe(0);
    expect(fakePlatform.openPositionsOf('flow-alfa')).toHaveLength(1);
  });

  it('estimates on the capital the user writes', async () => {
    await renderApp({ account: 'anna', url: FLOW_PAGE });
    await click(CASH_OUT);

    await userEvent.type(
      within(await confirmation()).getByLabelText('Capitale da mantenere (USDC, facoltativo)'),
      '400',
    );

    expect(await confirmation()).toHaveTextContent('liberare circa 220 USDC?');
  });

  it('keeps the estimate on the capital of now while the capital written is not a number', async () => {
    await renderApp({ account: 'anna', url: FLOW_PAGE });
    await click(CASH_OUT);

    await userEvent.type(
      within(await confirmation()).getByLabelText('Capitale da mantenere (USDC, facoltativo)'),
      '4a',
    );

    expect(await confirmation()).toHaveTextContent('liberare circa 120 USDC?');
  });

  it('cashes out once the user confirms and says what it freed', async () => {
    await renderApp({ account: 'anna', url: FLOW_PAGE });
    await click(CASH_OUT);

    await click("Conferma l'incasso");

    expect(await screen.findByText('Profitti incassati: liberati 120 USDC.')).toBeInTheDocument();
    expect(fakePlatform.cashOutsOf('alfa')).toBe(1);
    expect(fakePlatform.openPositionsOf('flow-alfa')).toEqual([]);
    expect(screen.queryByRole('alertdialog', { name: CONFIRMATION })).toBeNull();
    expect(within(await commands()).queryByRole('button', { name: CASH_OUT })).toBeNull();
  });

  it('keeps the capital the user wrote', async () => {
    await renderApp({ account: 'anna', url: FLOW_PAGE });
    await click(CASH_OUT);
    await userEvent.type(
      within(await confirmation()).getByLabelText('Capitale da mantenere (USDC, facoltativo)'),
      '400',
    );

    await click("Conferma l'incasso");

    expect(await screen.findByText('Profitti incassati: liberati 220 USDC.')).toBeInTheDocument();
    expect(fakePlatform.flowNamed('alfa').allocatedCapital).toBe(400);
  });

  it('frees nothing with a position left open, and says which and why', async () => {
    server.use(
      http.post('*/flows/:flowId/cash-out', () =>
        HttpResponse.json({
          flow: {},
          freed: null,
          capital: '500',
          left_open: [{ asset: 'BTC', reason: 'Order rejected' }],
        }),
      ),
    );
    await renderApp({ account: 'anna', url: FLOW_PAGE });
    await click(CASH_OUT);

    await click("Conferma l'incasso");

    const outcome = await screen.findByRole('alert');
    expect(outcome).toHaveTextContent('Incasso non completato: nessun capitale liberato.');
    expect(outcome).toHaveTextContent('La posizione su BTC non è stata chiusa: Order rejected');
  });

  it('shows the reason the API gives for a cash-out it refuses', async () => {
    server.use(
      http.post('*/flows/:flowId/cash-out', () =>
        HttpResponse.json({ detail: 'alfa non ha profitti da incassare' }, { status: 409 }),
      ),
    );
    await renderApp({ account: 'anna', url: FLOW_PAGE });
    await click(CASH_OUT);

    await click("Conferma l'incasso");

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Incasso non riuscito: alfa non ha profitti da incassare',
    );
  });

  it('closes nothing when the user cancels', async () => {
    await renderApp({ account: 'anna', url: FLOW_PAGE });
    await click(CASH_OUT);

    await click('Annulla');

    expect(screen.queryByRole('alertdialog', { name: CONFIRMATION })).toBeNull();
    expect(fakePlatform.cashOutsOf('alfa')).toBe(0);
  });
});
