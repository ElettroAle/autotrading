import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';

import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

describe('FlowsList', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addUser('bruno', { hasUserRole: true });
    fakePlatform.addFlow('bruno', 'omega');
  });

  it('lists the flows of the tenant of the user, each leading to its page', async () => {
    fakePlatform.addFlow('anna', 'alfa');
    await renderApp({ account: 'anna' });

    const flows = await screen.findByRole('list', { name: 'Flussi' });
    expect(within(flows).getByRole('link', { name: 'alfa' })).toHaveAttribute(
      'href',
      '/flows/flow-alfa',
    );
    expect(within(flows).getByText('attivo')).toBeInTheDocument();
    expect(screen.queryByText('omega')).not.toBeInTheDocument();
  });

  it('says the user has no flow yet', async () => {
    await renderApp({ account: 'anna' });

    expect(await screen.findByText('Non hai ancora flussi.')).toBeInTheDocument();
  });

  it('tells why the flows could not be read', async () => {
    server.use(
      http.get('*/flows', () => HttpResponse.json({ detail: 'errore interno' }, { status: 500 })),
    );
    await renderApp({ account: 'anna' });

    expect(await screen.findByRole('alert')).toHaveTextContent('errore interno');
  });
});
