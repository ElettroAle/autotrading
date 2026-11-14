import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';

import { RuntimeConfigProvider } from '@/config/runtime-config';
import { TEST_CONFIG } from '@/testing/test-utils';

import { DashboardLayout } from './dashboard-layout';

const renderLayout = () => {
  const router = createMemoryRouter([
    {
      path: '/',
      element: (
        <DashboardLayout title="I tuoi flussi">
          <p>contenuto</p>
        </DashboardLayout>
      ),
    },
  ]);
  render(
    <RuntimeConfigProvider config={TEST_CONFIG}>
      <QueryClientProvider client={new QueryClient()}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </RuntimeConfigProvider>,
  );
};

describe('DashboardLayout', () => {
  it('shows the title, the content, the environment and the command to reread the data', () => {
    renderLayout();

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('I tuoi flussi');
    expect(screen.getByText('contenuto')).toBeInTheDocument();
    expect(screen.getByLabelText("Ambiente dell'installazione")).toHaveTextContent('dev');
    expect(screen.getByRole('button', { name: 'Aggiorna' })).toBeInTheDocument();
  });

  it('leads to the pages of the dashboard from its navigation', () => {
    renderLayout();

    const navigation = screen.getByRole('navigation', { name: 'Navigazione' });
    expect(navigation).toContainElement(screen.getByRole('link', { name: 'Flussi' }));
    expect(screen.getByRole('link', { name: 'Flussi' })).toHaveAttribute('href', '/');
  });

  it('keeps the navigation at the side on a wide screen and folds it into a menu on a narrow one', () => {
    renderLayout();

    expect(screen.getByRole('navigation', { name: 'Navigazione' })).toHaveClass(
      'hidden',
      'md:block',
    );
    expect(screen.getByRole('button', { name: 'Menu' })).toHaveClass('md:hidden');
  });

  it('opens and closes the menu on a narrow screen', async () => {
    renderLayout();
    const menu = screen.getByRole('button', { name: 'Menu' });

    await userEvent.click(menu);

    expect(menu).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('navigation', { name: 'Navigazione' })).not.toHaveClass('hidden');

    await userEvent.click(menu);

    expect(menu).toHaveAttribute('aria-expanded', 'false');
    expect(screen.getByRole('navigation', { name: 'Navigazione' })).toHaveClass('hidden');
  });
});
