import { render, screen, within } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';

import { FlowViewTabs } from './flow-view-tabs';

describe('FlowViewTabs', () => {
  it('shows the list and the ranking of the flows as views', () => {
    const router = createMemoryRouter([{ path: '*', element: <FlowViewTabs /> }], {
      initialEntries: ['/ranking'],
    });
    render(<RouterProvider router={router} />);

    const views = screen.getByRole('navigation', { name: 'Viste dei flussi' });
    expect(within(views).getByRole('link', { name: 'Elenco' })).toHaveAttribute('href', '/');
    expect(within(views).getByRole('link', { name: 'Classifica' })).toHaveAttribute(
      'aria-current',
      'page',
    );
  });
});
