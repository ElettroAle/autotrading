import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { GO_COMMAND } from '@/components/ui/commands';
import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const detail = (label: string) =>
  within(screen.getByLabelText('Configurazione')).getByText(label, { selector: 'dt' })
    .nextElementSibling?.textContent;

// The configuration in force is in the settings of the flow, behind the gear of its page (Bug 560).
const openConfiguration = async () =>
  userEvent.click(await screen.findByRole('link', { name: 'Impostazioni del flusso' }));

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
    expect(screen.queryByRole('button', { name: 'Avvia' })).not.toBeInTheDocument();
    expect(screen.queryByRole('note', { name: 'Da configurare' })).not.toBeInTheDocument();
    await openConfiguration();

    await waitFor(() => expect(detail('Conto')).toBe('principale'));
    expect(detail('Versione')).toBe('1');
    expect(detail('Modello')).toBe('openrouter/deepseek-chat');
    expect(detail('Fonti')).toBe('indicatori (peso 2)');
    expect(detail('Capitale allocato')).toBe('100 USDC');
    expect(detail('Asset')).toBe('BTC');
  });

  it('duplicates the flow and opens the draft, labelled, with account and capital of the original and no assets', async () => {
    const { router } = await renderApp({ account: 'anna', url: '/flows/flow-alfa/settings' });

    await userEvent.click(await screen.findByRole('button', { name: 'Duplica' }));

    await waitFor(() => expect(router.state.location.pathname).toBe('/flows/flow-alfa%20(copia)'));
    expect(await screen.findByRole('heading', { level: 1, name: 'alfa (copia)' })).toBeVisible();
    expect(await screen.findByText('Bozza')).toBeInTheDocument();
    await openConfiguration();
    await screen.findByRole('heading', { level: 1, name: 'Impostazioni di alfa (copia)' });
    expect(detail('Versione')).toBe('1');
    expect(detail('Fonti')).toBe('indicatori (peso 2)');
    expect([detail('Conto'), detail('Capitale allocato'), detail('Asset')]).toEqual([
      'principale',
      '100 USDC',
      'da assegnare',
    ]);
  });

  it('tells why the flow could not be duplicated', async () => {
    fakePlatform.duplicate(fakePlatform.user('anna'), 'flow-alfa');
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/settings' });

    await userEvent.click(await screen.findByRole('button', { name: 'Duplica' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Duplicazione rifiutata: nome già usato da un altro flusso',
    );
  });

  it('says on the overview of the copy what it lacks to start and leads to its configuration', async () => {
    fakePlatform.duplicate(fakePlatform.user('anna'), 'flow-alfa');
    const { router } = await renderApp({ account: 'anna', url: '/flows/flow-alfa%20(copia)' });

    const note = await screen.findByRole('note', { name: 'Da configurare' });
    expect(note).toHaveTextContent("Prima dell'avvio manca: asset");
    expect(screen.queryByRole('form')).not.toBeInTheDocument();
    await userEvent.click(within(note).getByRole('link', { name: 'Configura' }));

    expect(router.state.location.pathname).toBe('/flows/flow-alfa%20(copia)/edit');
  });

  it('names the account by its identifier while the accounts cannot be read', async () => {
    server.use(http.get('*/accounts', () => HttpResponse.json({}, { status: 503 })));
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/settings' });

    await waitFor(() => expect(detail('Conto')).toBe('account-principale'));
  });

  it('starts the assigned draft', async () => {
    const anna = fakePlatform.user('anna');
    const copy = fakePlatform.duplicate(anna, 'flow-alfa');
    fakePlatform.changeFlow(copy.name, { accountId: 'account-secondario', assets: ['BTC'] });
    await renderApp({ account: 'anna', url: '/flows/flow-alfa%20(copia)' });

    await userEvent.click(await screen.findByRole('button', { name: 'Avvia' }));

    expect(await screen.findByText('Stato: attivo')).toBeInTheDocument();
    expect(screen.queryByText('Bozza')).not.toBeInTheDocument();
  });

  it('offers to start the assigned draft in green with the icon play (R6.5.3)', async () => {
    const anna = fakePlatform.user('anna');
    const copy = fakePlatform.duplicate(anna, 'flow-alfa');
    fakePlatform.changeFlow(copy.name, { accountId: 'account-secondario', assets: ['BTC'] });
    await renderApp({ account: 'anna', url: '/flows/flow-alfa%20(copia)' });

    const start = await screen.findByRole('button', { name: 'Avvia' });

    expect(start).toHaveAttribute('class', GO_COMMAND);
    expect(within(start).getByRole('img', { hidden: true })).toHaveAttribute('data-icon', 'play');
  });

  it('starts a draft on an account that trades real money only once the user confirms it', async () => {
    fakePlatform.configureExchangeNetwork('real');
    const anna = fakePlatform.user('anna');
    const copy = fakePlatform.duplicate(anna, 'flow-alfa');
    fakePlatform.changeFlow(copy.name, { accountId: 'account-secondario', assets: ['BTC'] });
    await renderApp({ account: 'anna', url: '/flows/flow-alfa%20(copia)' });

    await userEvent.click(await screen.findByRole('button', { name: 'Avvia' }));
    const confirmation = await screen.findByRole('alertdialog', { name: "Conferma dell'avvio" });
    expect(confirmation).toHaveTextContent('Il flusso opererà con denaro reale');
    expect(screen.getByText('Bozza')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Avvia con denaro reale' }));

    expect(await screen.findByText('Stato: attivo')).toBeInTheDocument();
  });

  it('keeps the draft when the user does not confirm the start on real money', async () => {
    fakePlatform.configureExchangeNetwork('real');
    const anna = fakePlatform.user('anna');
    const copy = fakePlatform.duplicate(anna, 'flow-alfa');
    fakePlatform.changeFlow(copy.name, { accountId: 'account-secondario', assets: ['BTC'] });
    await renderApp({ account: 'anna', url: '/flows/flow-alfa%20(copia)' });

    await userEvent.click(await screen.findByRole('button', { name: 'Avvia' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Annulla' }));

    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(screen.getByText('Bozza')).toBeInTheDocument();
  });

  it('tells why the draft does not start', async () => {
    const copy = fakePlatform.duplicate(fakePlatform.user('anna'), 'flow-alfa');
    fakePlatform.changeFlow(copy.name, { assets: ['BTC'] });
    await renderApp({ account: 'anna', url: '/flows/flow-alfa%20(copia)' });

    await userEvent.click(await screen.findByRole('button', { name: 'Avvia' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Avvio rifiutato: asset già assegnati al flusso alfa sullo stesso conto: BTC',
    );
    expect(screen.getByText('Bozza')).toBeInTheDocument();
  });

  // ADR mancanze-della-bozza-dichiarate-dall-api: what the draft lacks comes from the API, which disables Avvia.
  it('keeps Avvia disabled while the draft lacks something, saying what and leading to its configuration', async () => {
    fakePlatform.addFlow('anna', 'vuota', { status: 'bozza', allocatedCapital: null, assets: [] });
    fakePlatform.changeFlow('vuota', { accountId: null });
    const { router } = await renderApp({ account: 'anna', url: '/flows/flow-vuota' });

    const start = await screen.findByRole('button', { name: 'Avvia' });
    expect(start).toBeDisabled();
    const missing = screen.getByRole('group', { name: 'Avvio della bozza' });
    expect(missing).toHaveTextContent('Per avviarla manca: conto, capitale allocato e asset');
    await userEvent.click(within(missing).getByRole('link', { name: 'Configura' }));

    expect(router.state.location.pathname).toBe('/flows/flow-vuota/edit');
    expect(fakePlatform.flowNamed('vuota').status).toBe('bozza');
  });

  it('enables Avvia without a list once the draft lacks nothing', async () => {
    const copy = fakePlatform.duplicate(fakePlatform.user('anna'), 'flow-alfa');
    fakePlatform.changeFlow(copy.name, { assets: ['ETH'] });
    await renderApp({ account: 'anna', url: '/flows/flow-alfa%20(copia)' });

    expect(await screen.findByRole('button', { name: 'Avvia' })).toBeEnabled();
    expect(screen.queryByText(/Per avviarla manca/)).not.toBeInTheDocument();
  });
});
