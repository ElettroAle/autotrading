import { screen } from '@testing-library/react';
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
});
