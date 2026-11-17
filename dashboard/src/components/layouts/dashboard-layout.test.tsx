import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';

import { RuntimeConfigProvider } from '@/config/runtime-config';
import { TEST_CONFIG } from '@/testing/test-utils';

import { DashboardLayout } from './dashboard-layout';

const renderLayout = (url = '/') => {
  const router = createMemoryRouter(
    [
      {
        path: '*',
        element: (
          <DashboardLayout title="I tuoi flussi">
            <p>contenuto</p>
          </DashboardLayout>
        ),
      },
    ],
    { initialEntries: [url] },
  );
  render(
    <RuntimeConfigProvider config={TEST_CONFIG}>
      <QueryClientProvider client={new QueryClient()}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </RuntimeConfigProvider>,
  );
};

const currentEntries = (navigation: HTMLElement) =>
  within(navigation)
    .getAllByRole('link')
    .filter((link) => link.getAttribute('aria-current') === 'page')
    .map((link) => link.textContent);

describe('DashboardLayout', () => {
  it('shows the title, the content, the environment and the command to reread the data', () => {
    renderLayout();

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('I tuoi flussi');
    expect(screen.getByText('contenuto')).toBeInTheDocument();
    expect(screen.getByLabelText("Ambiente dell'installazione")).toHaveTextContent('dev');
    expect(screen.getByRole('button', { name: 'Aggiorna' })).toBeInTheDocument();
  });

  // ADR accesso-persistente-con-cache-msal-in-localstorage: «Esci» lives in the shared layout, on every page of the data.
  it('offers the way out in the navigation of the page', () => {
    renderLayout();

    expect(
      within(screen.getByRole('navigation', { name: 'Navigazione' })).getByRole('button', {
        name: 'Esci',
      }),
    ).toBeInTheDocument();
  });

  it('breaks a title with a long word instead of pushing the page wider', () => {
    renderLayout();

    expect(screen.getByRole('heading', { level: 1 })).toHaveClass('wrap-anywhere');
  });

  it('leads to every area of the dashboard from its navigation', () => {
    renderLayout();

    const navigation = screen.getByRole('navigation', { name: 'Navigazione' });
    expect(within(navigation).getByRole('link', { name: 'Flussi' })).toHaveAttribute('href', '/');
    expect(within(navigation).getByRole('link', { name: 'Conti' })).toHaveAttribute(
      'href',
      '/accounts',
    );
    expect(within(navigation).getByRole('link', { name: 'Storico' })).toHaveAttribute(
      'href',
      '/history',
    );
    expect(within(navigation).getByRole('link', { name: 'Chiavi' })).toHaveAttribute(
      'href',
      '/provider-keys',
    );
    expect(within(navigation).getByRole('link', { name: 'Notifiche' })).toHaveAttribute(
      'href',
      '/notifications',
    );
  });

  it('gathers the settings under a visible heading', () => {
    renderLayout();

    const settings = screen.getByRole('list', { name: 'Impostazioni' });
    expect(screen.getByText('Impostazioni')).toBeVisible();
    expect(
      within(settings)
        .getAllByRole('link')
        .map((link) => link.textContent),
    ).toEqual(['Chiavi', 'Notifiche']);
    expect(within(settings).queryByRole('link', { name: 'Flussi' })).toBeNull();
  });

  it.each([
    ['/', 'Flussi'],
    ['/flows/flow-alfa', 'Flussi'],
    ['/flows/flow-alfa/cycles/2026-11-14T10:00:00Z', 'Flussi'],
    ['/flows/new', 'Flussi'],
    ['/ranking', 'Flussi'],
    ['/comparison?flow=flow-alfa', 'Flussi'],
    ['/accounts', 'Conti'],
    ['/history?tab=orders', 'Storico'],
    ['/provider-keys', 'Chiavi'],
    ['/notifications', 'Notifiche'],
  ])('marks the entry of the area of %s, and only that one', (url, entry) => {
    renderLayout(url);

    const navigation = screen.getByRole('navigation', { name: 'Navigazione' });
    expect(within(navigation).getByRole('link', { name: entry })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(currentEntries(navigation)).toEqual([entry]);
  });

  it('marks no entry on a page of no area', () => {
    renderLayout('/accountsx');

    const navigation = screen.getByRole('navigation', { name: 'Navigazione' });
    expect(currentEntries(navigation)).toEqual([]);
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
