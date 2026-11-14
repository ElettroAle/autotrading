import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const detail = (label: string) =>
  within(screen.getByLabelText('Configurazione')).getByText(label, { selector: 'dt' })
    .nextElementSibling?.textContent;

const assignmentForm = () => screen.getByRole('form', { name: 'Assegnazione della bozza' });

describe('Draft flows', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addFlow('anna', 'alfa', {
      model: 'openrouter/deepseek-chat',
      sources: [{ name: 'indicatori', weight: 2 }],
    });
    fakePlatform.addAccount('anna', 'secondario');
  });

  it('shows the configuration in force of a flow with its account', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await screen.findByText('Stato: attivo')).toBeInTheDocument();
    await waitFor(() => expect(detail('Conto')).toBe('principale'));
    expect(detail('Versione')).toBe('1');
    expect(detail('Modello')).toBe('openrouter/deepseek-chat');
    expect(detail('Fonti')).toBe('indicatori (peso 2)');
    expect(detail('Capitale allocato')).toBe('100 USDC');
    expect(detail('Asset')).toBe('BTC');
    expect(screen.queryByRole('button', { name: 'Avvia' })).not.toBeInTheDocument();
    expect(
      screen.queryByRole('form', { name: 'Assegnazione della bozza' }),
    ).not.toBeInTheDocument();
  });

  it('duplicates the flow and opens the draft, labelled and without account, capital or assets', async () => {
    const { router } = await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    await userEvent.click(await screen.findByRole('button', { name: 'Duplica' }));

    await waitFor(() => expect(router.state.location.pathname).toBe('/flows/flow-alfa%20(copia)'));
    expect(await screen.findByRole('heading', { level: 2, name: 'alfa (copia)' })).toBeVisible();
    expect(screen.getByText('Bozza')).toBeInTheDocument();
    expect(detail('Versione')).toBe('1');
    expect(detail('Fonti')).toBe('indicatori (peso 2)');
    expect([detail('Conto'), detail('Capitale allocato'), detail('Asset')]).toEqual([
      'da assegnare',
      'da assegnare',
      'da assegnare',
    ]);
  });

  it('tells why the flow could not be duplicated', async () => {
    fakePlatform.duplicate(fakePlatform.user('anna'), 'flow-alfa');
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    await userEvent.click(await screen.findByRole('button', { name: 'Duplica' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Duplicazione rifiutata: nome già usato da un altro flusso',
    );
  });

  it('assigns account, capital and assets to the draft as its next version', async () => {
    fakePlatform.duplicate(fakePlatform.user('anna'), 'flow-alfa');
    await renderApp({ account: 'anna', url: '/flows/flow-alfa%20(copia)' });

    await userEvent.selectOptions(await screen.findByLabelText('Conto'), 'secondario');
    await userEvent.type(screen.getByLabelText('Capitale allocato (USDC)'), '200');
    await userEvent.type(screen.getByLabelText('Asset'), 'btc, eth');
    await userEvent.click(screen.getByRole('button', { name: 'Assegna' }));

    await waitFor(() => expect(detail('Conto')).toBe('secondario'));
    expect(detail('Versione')).toBe('2');
    expect(detail('Capitale allocato')).toBe('200 USDC');
    expect(detail('Asset')).toBe('BTC, ETH');
  });

  it('asks for every field of the assignment before sending it', async () => {
    fakePlatform.duplicate(fakePlatform.user('anna'), 'flow-alfa');
    await renderApp({ account: 'anna', url: '/flows/flow-alfa%20(copia)' });

    await userEvent.type(await screen.findByLabelText('Capitale allocato (USDC)'), '-3');
    await userEvent.click(screen.getByRole('button', { name: 'Assegna' }));

    const form = assignmentForm();
    expect(await within(form).findByText('scegli un conto')).toBeInTheDocument();
    expect(within(form).getByText('il capitale allocato deve essere positivo')).toBeInTheDocument();
    expect(within(form).getByText('almeno un asset è obbligatorio')).toBeInTheDocument();
    expect(detail('Versione')).toBe('1');
  });

  it('shows the refusal of the API beside the form', async () => {
    fakePlatform.duplicate(fakePlatform.user('anna'), 'flow-alfa');
    await renderApp({ account: 'anna', url: '/flows/flow-alfa%20(copia)' });

    await userEvent.selectOptions(await screen.findByLabelText('Conto'), 'secondario');
    await userEvent.type(screen.getByLabelText('Capitale allocato (USDC)'), '5000');
    await userEvent.type(screen.getByLabelText('Asset'), 'BTC');
    await userEvent.click(screen.getByRole('button', { name: 'Assegna' }));

    expect(await within(assignmentForm()).findByRole('alert')).toHaveTextContent(
      'capitale allocato oltre il capitale libero: 1000 USDC',
    );
  });

  it('shows beside each field what the API finds invalid in it', async () => {
    server.use(
      http.put('*/flows/:flowId/assignment', () =>
        HttpResponse.json(
          {
            detail: 'richiesta non valida',
            errors: [{ loc: ['body', 'allocated_capital'], msg: 'numero non valido' }],
          },
          { status: 422 },
        ),
      ),
    );
    fakePlatform.duplicate(fakePlatform.user('anna'), 'flow-alfa');
    await renderApp({ account: 'anna', url: '/flows/flow-alfa%20(copia)' });

    await userEvent.selectOptions(await screen.findByLabelText('Conto'), 'secondario');
    await userEvent.type(screen.getByLabelText('Capitale allocato (USDC)'), '200');
    await userEvent.type(screen.getByLabelText('Asset'), 'BTC');
    await userEvent.click(screen.getByRole('button', { name: 'Assegna' }));

    expect(await within(assignmentForm()).findByText('numero non valido')).toBeInTheDocument();
    expect(within(assignmentForm()).getByRole('alert')).toHaveTextContent('richiesta non valida');
  });

  it('keeps at form level what the API finds invalid outside the fields of the form', async () => {
    server.use(
      http.put('*/flows/:flowId/assignment', () =>
        HttpResponse.json(
          { detail: 'richiesta non valida', errors: [{ loc: ['body'], msg: 'corpo assente' }] },
          { status: 422 },
        ),
      ),
    );
    fakePlatform.duplicate(fakePlatform.user('anna'), 'flow-alfa');
    await renderApp({ account: 'anna', url: '/flows/flow-alfa%20(copia)' });

    await userEvent.selectOptions(await screen.findByLabelText('Conto'), 'secondario');
    await userEvent.type(screen.getByLabelText('Capitale allocato (USDC)'), '200');
    await userEvent.type(screen.getByLabelText('Asset'), 'BTC');
    await userEvent.click(screen.getByRole('button', { name: 'Assegna' }));

    expect(await within(assignmentForm()).findByRole('alert')).toHaveTextContent(
      'richiesta non valida',
    );
    expect(within(assignmentForm()).queryByText('corpo assente')).not.toBeInTheDocument();
  });

  it('names the account by its identifier while the accounts cannot be read', async () => {
    server.use(http.get('*/accounts', () => HttpResponse.json({}, { status: 503 })));
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await screen.findByText('Stato: attivo')).toBeInTheDocument();
    await waitFor(() => expect(detail('Conto')).toBe('account-principale'));
  });

  it('starts the assigned draft', async () => {
    const anna = fakePlatform.user('anna');
    const copy = fakePlatform.duplicate(anna, 'flow-alfa');
    fakePlatform.assign(anna, copy.id, {
      accountId: 'account-secondario',
      allocatedCapital: 200,
      assets: ['BTC'],
    });
    await renderApp({ account: 'anna', url: '/flows/flow-alfa%20(copia)' });

    await userEvent.click(await screen.findByRole('button', { name: 'Avvia' }));

    expect(await screen.findByText('Stato: attivo')).toBeInTheDocument();
    expect(screen.queryByText('Bozza')).not.toBeInTheDocument();
  });

  it('tells why the draft does not start', async () => {
    fakePlatform.duplicate(fakePlatform.user('anna'), 'flow-alfa');
    await renderApp({ account: 'anna', url: '/flows/flow-alfa%20(copia)' });

    await userEvent.click(await screen.findByRole('button', { name: 'Avvia' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Avvio rifiutato: conto, capitale allocato e asset mancanti',
    );
    expect(screen.getByText('Bozza')).toBeInTheDocument();
  });
});
