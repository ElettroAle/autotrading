import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

describe('FlowView', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addFlow('anna', 'alfa');
  });

  it('titles the page with the name of the flow and shows its status', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await screen.findByRole('heading', { level: 1, name: 'alfa' })).toBeInTheDocument();
    expect(screen.getByText('Stato: attivo')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Versioni della configurazione' })).toHaveAttribute(
      'href',
      '/flows/flow-alfa/versions',
    );
  });

  it('warns that a flow on the test network trades no real money', async () => {
    fakePlatform.configureExchangeNetwork('test', 'sandbox');
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await screen.findByRole('note')).toHaveTextContent(
      'Il flusso opererà sulla rete di test "sandbox", senza denaro reale',
    );
  });

  it('shows no warning of the test network for a flow on real money', async () => {
    fakePlatform.configureExchangeNetwork('real');
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await screen.findByRole('heading', { level: 1, name: 'alfa' })).toBeInTheDocument();
    expect(screen.queryByText(/rete di test/)).not.toBeInTheDocument();
  });

  it('leads to the cycles of the flow', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await screen.findByRole('link', { name: 'Cicli del flusso' })).toHaveAttribute(
      'href',
      '/flows/flow-alfa/cycles',
    );
  });

  it('leads to the open and the closed positions of the flow', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await screen.findByRole('link', { name: 'Posizioni aperte' })).toHaveAttribute(
      'href',
      '/flows/flow-alfa/positions',
    );
    expect(screen.getByRole('link', { name: 'Posizioni chiuse' })).toHaveAttribute(
      'href',
      '/flows/flow-alfa/closed-positions',
    );
  });

  it('leads to the editor of the configuration of the flow', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await screen.findByRole('link', { name: 'Modifica la configurazione' })).toHaveAttribute(
      'href',
      '/flows/flow-alfa/edit',
    );
  });

  it('says a flow outside the tenant of the user does not exist, under the generic title', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-omega' });

    expect(await screen.findByText('Flusso non trovato.')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/^Flusso$/);
  });

  it('shows the views of the flow as tabs, apart from the command that edits it', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    const views = await screen.findByRole('navigation', { name: 'Dati del flusso' });
    expect(
      within(views)
        .getAllByRole('link')
        .map((link) => link.textContent),
    ).toEqual([
      'Posizioni aperte',
      'Posizioni chiuse',
      'Cicli del flusso',
      'Versioni della configurazione',
    ]);
    const edit = screen.getByRole('link', { name: 'Modifica la configurazione' });
    expect(views).not.toContainElement(edit);
    expect(edit).toHaveClass('min-h-11');
  });

  it('shows the status and the warning of the network before views, commands and configuration', async () => {
    fakePlatform.configureExchangeNetwork('test', 'sandbox');
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    const status = await screen.findByText('Stato: attivo');
    const notice = screen.getByRole('note');
    const views = screen.getByRole('navigation', { name: 'Dati del flusso' });
    const commands = await screen.findByRole('group', { name: 'Comandi del flusso' });
    const configuration = screen.getByLabelText('Configurazione', { exact: true });
    const order = [status, notice, views, commands, configuration];
    order.slice(1).forEach((element, index) => {
      expect(order[index]?.compareDocumentPosition(element)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    });
  });

  it('tells why the flow could not be read', async () => {
    server.use(
      http.get('*/flows', () => HttpResponse.json({ detail: 'errore interno' }, { status: 500 })),
    );
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await screen.findByRole('alert')).toHaveTextContent('errore interno');
  });

  it('keeps showing the flow and its cycles when a rereading fails', async () => {
    fakePlatform.concludeCycle('alfa', new Date(2026, 10, 14, 9, 45, 0));
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });
    await screen.findByRole('list', { name: 'Cicli recenti' });
    fakePlatform.stopApi();

    await userEvent.click(screen.getByRole('button', { name: 'Aggiorna' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Dati non aggiornati');
    expect(screen.getByRole('heading', { level: 1, name: 'alfa' })).toBeInTheDocument();
    expect(screen.getByRole('list', { name: 'Cicli recenti' })).toHaveTextContent('09:45:00');
  });

  it('keeps a long name of a model within the configuration, breaking it where it does not fit', async () => {
    fakePlatform.changeFlow('alfa', { model: 'openrouter/~deepseek/deepseek-flash-latest' });
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    const configuration = await screen.findByLabelText('Configurazione', { exact: true });
    expect(configuration).toHaveClass('grid-cols-[max-content_minmax(0,1fr)]');
    expect(
      within(configuration).getByText('openrouter/~deepseek/deepseek-flash-latest'),
    ).toHaveClass('min-w-0', 'wrap-anywhere');
  });
});
