import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { fakePlatform } from '@/testing/mocks/platform';
import { renderApp } from '@/testing/test-utils';

const OTHER_AREAS = ['/accounts', '/history', '/provider-keys', '/notifications'];

describe('HomeRoute', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
  });

  it('is the list of the flows, a view beside the ranking', async () => {
    await renderApp({ account: 'anna' });

    const views = await screen.findByRole('navigation', { name: 'Viste dei flussi' });
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('I tuoi flussi');
    expect(within(views).getByRole('link', { name: 'Elenco' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(within(views).getByRole('link', { name: 'Classifica' })).toHaveAttribute(
      'href',
      '/ranking',
    );
  });

  it('leads to a new flow from its actions', async () => {
    const { router } = await renderApp({ account: 'anna' });

    await userEvent.click(await screen.findByRole('link', { name: 'Nuovo flusso' }));

    expect(router.state.location.pathname).toBe('/flows/new');
  });

  it('has no link to the other areas of the dashboard: the menu leads there', async () => {
    await renderApp({ account: 'anna' });

    await screen.findByRole('navigation', { name: 'Viste dei flussi' });
    const content = screen.getByRole('main');
    const hrefs = within(content)
      .getAllByRole('link')
      .map((link) => link.getAttribute('href') ?? '');
    expect(hrefs.filter((href) => OTHER_AREAS.some((area) => href.startsWith(area)))).toEqual([]);
  });
});
