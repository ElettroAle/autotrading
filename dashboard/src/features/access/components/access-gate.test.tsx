import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';

import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

describe('AccessGate', () => {
  it('opens the pages to a user the API admits', async () => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    await renderApp({ account: 'anna' });

    expect(await screen.findByRole('heading', { name: 'I tuoi flussi' })).toBeInTheDocument();
  });

  it('tells a user without the Utente role that the access is not allowed, showing no data', async () => {
    fakePlatform.addUser('carla', { hasUserRole: false });
    await renderApp({ account: 'carla' });

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Accesso non consentito: manca il ruolo Utente',
    );
    expect(screen.queryByRole('list', { name: 'Flussi' })).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'I tuoi flussi' })).not.toBeInTheDocument();
  });

  it('tells why the platform could not admit the user', async () => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    server.use(
      http.get('*/me', () =>
        HttpResponse.json({ detail: 'autenticazione non configurata' }, { status: 503 }),
      ),
    );
    await renderApp({ account: 'anna' });

    expect(await screen.findByRole('alert')).toHaveTextContent('autenticazione non configurata');
    expect(screen.queryByRole('heading', { name: 'I tuoi flussi' })).not.toBeInTheDocument();
  });

  it('shows nothing of the pages while the API has not answered', async () => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    await renderApp({ account: 'anna' });

    expect(await screen.findByRole('status')).toHaveTextContent('Caricamento…');
    expect(await screen.findByRole('heading', { name: 'I tuoi flussi' })).toBeInTheDocument();
  });
});
