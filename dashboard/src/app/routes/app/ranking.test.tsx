import { screen, within } from '@testing-library/react';

import { fakePlatform } from '@/testing/mocks/platform';
import { renderApp } from '@/testing/test-utils';

describe('RankingRoute', () => {
  it('is a view of the flows, beside their list', async () => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    await renderApp({ account: 'anna', url: '/ranking' });

    const views = await screen.findByRole('navigation', { name: 'Viste dei flussi' });
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('I tuoi flussi');
    expect(within(views).getByRole('link', { name: 'Classifica' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(within(views).getByRole('link', { name: 'Elenco' })).toHaveAttribute('href', '/');
  });
});
