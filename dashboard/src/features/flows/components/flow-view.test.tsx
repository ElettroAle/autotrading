import { screen } from '@testing-library/react';
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

  it('shows the name and the status of the flow', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await screen.findByRole('heading', { level: 2 })).toHaveTextContent('alfa');
    expect(screen.getByText('Stato: attivo')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Versioni della configurazione' })).toHaveAttribute(
      'href',
      '/flows/flow-alfa/versions',
    );
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

  it('says a flow outside the tenant of the user does not exist', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-omega' });

    expect(await screen.findByText('Flusso non trovato.')).toBeInTheDocument();
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
    expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('alfa');
    expect(screen.getByRole('list', { name: 'Cicli recenti' })).toHaveTextContent('09:45:00');
  });
});
