import { screen } from '@testing-library/react';

import { renderApp } from '@/testing/test-utils';

describe('NotFoundRoute', () => {
  it('tells the page does not exist and leads back to the flows', async () => {
    await renderApp({ url: '/pagina/inesistente' });

    expect(await screen.findByRole('heading', { name: 'Pagina non trovata' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Torna ai tuoi flussi' })).toHaveAttribute('href', '/');
  });
});
