import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { createMemoryRouter, RouterProvider } from 'react-router';

import { ViewTabs } from './view-tabs';

const VIEWS = [
  { name: 'Elenco', to: '/' },
  { name: 'Classifica', to: '/ranking' },
] as const;

const TABS = [
  { key: 'cycles', name: 'Cicli' },
  { key: 'closed-positions', name: 'Posizioni chiuse' },
  { key: 'orders', name: 'Ordini' },
] as const;

type Kind = (typeof TABS)[number]['key'];

const openAt = (url: string) => {
  const router = createMemoryRouter(
    [{ path: '*', element: <ViewTabs label="Viste dei flussi" views={VIEWS} /> }],
    { initialEntries: [url] },
  );
  render(<RouterProvider router={router} />);
  return router;
};

const PageTabs = ({ first, chosen }: { first: Kind; chosen: Kind[] }) => {
  const [current, setCurrent] = useState<Kind>(first);
  return (
    <ViewTabs
      label="Storici"
      tabs={TABS}
      current={current}
      choose={(kind) => {
        chosen.push(kind);
        setCurrent(kind);
      }}
    />
  );
};

const showTabs = (first: Kind = 'cycles') => {
  const chosen: Kind[] = [];
  render(<PageTabs first={first} chosen={chosen} />);
  return chosen;
};

const tab = (name: string) => screen.getByRole('tab', { name });

// ADR schede-con-aspetto-e-ruolo-di-schede: one component gives every tab of the dashboard the look and the role of a
// tab, whether the tabs are pages of their own or views of the same page.
describe('ViewTabs, ADR schede-con-aspetto-e-ruolo-di-schede', () => {
  describe('with views that are pages of their own', () => {
    it('shows every view as a link to its own address', () => {
      openAt('/');

      const views = screen.getByRole('navigation', { name: 'Viste dei flussi' });
      expect(views).toContainElement(screen.getByRole('link', { name: 'Elenco' }));
      expect(screen.getByRole('link', { name: 'Elenco' })).toHaveAttribute('href', '/');
      expect(screen.getByRole('link', { name: 'Classifica' })).toHaveAttribute('href', '/ranking');
    });

    it('marks the view of the current page, and only that one', () => {
      openAt('/ranking');

      expect(screen.getByRole('link', { name: 'Classifica' })).toHaveAttribute(
        'aria-current',
        'page',
      );
      expect(screen.getByRole('link', { name: 'Elenco' })).not.toHaveAttribute('aria-current');
    });

    it('moves to another view and marks it', async () => {
      const router = openAt('/');

      await userEvent.click(screen.getByRole('link', { name: 'Classifica' }));

      expect(router.state.location.pathname).toBe('/ranking');
      expect(screen.getByRole('link', { name: 'Classifica' })).toHaveAttribute(
        'aria-current',
        'page',
      );
    });

    it('puts the views on a bar of their own, the chosen one white with a blue mark', () => {
      openAt('/');

      const views = screen.getByRole('navigation', { name: 'Viste dei flussi' });
      expect(within(views).getByRole('list')).toHaveClass('bg-slate-100');
      expect(screen.getByRole('link', { name: 'Elenco' })).toHaveClass(
        'bg-white',
        'text-slate-900',
        'border-blue-700',
      );
      expect(screen.getByRole('link', { name: 'Classifica' })).toHaveClass(
        'border-transparent',
        'text-slate-600',
      );
      expect(screen.getByRole('link', { name: 'Classifica' })).not.toHaveClass('bg-white');
    });

    it('keeps the views on one row that scrolls inside itself on a narrow screen', () => {
      openAt('/');

      const views = screen.getByRole('navigation', { name: 'Viste dei flussi' });
      expect(views).toHaveClass('max-w-full', 'overflow-x-auto');
      expect(within(views).getByRole('list')).toHaveClass('flex-nowrap');
      expect(screen.getByRole('link', { name: 'Elenco' })).toHaveClass('whitespace-nowrap');
    });
  });

  describe('with views of the same page', () => {
    it('shows the views as tabs of a group of tabs, the current one selected', () => {
      showTabs('orders');

      const group = screen.getByRole('tablist', { name: 'Storici' });
      expect(
        within(group)
          .getAllByRole('tab')
          .map((each) => each.textContent),
      ).toEqual(['Cicli', 'Posizioni chiuse', 'Ordini']);
      expect(tab('Ordini')).toHaveAttribute('aria-selected', 'true');
      expect(tab('Cicli')).toHaveAttribute('aria-selected', 'false');
    });

    it('gives the tabs the same look as the views that are pages', () => {
      showTabs();

      expect(screen.getByRole('tablist', { name: 'Storici' })).toHaveClass('bg-slate-100');
      expect(tab('Cicli')).toHaveClass('bg-white', 'border-blue-700', 'whitespace-nowrap');
      expect(tab('Ordini')).toHaveClass('border-transparent', 'text-slate-600');
    });

    it('chooses the tab clicked', async () => {
      const chosen = showTabs();

      await userEvent.click(tab('Posizioni chiuse'));

      expect(chosen).toEqual(['closed-positions']);
      expect(tab('Posizioni chiuse')).toHaveAttribute('aria-selected', 'true');
    });

    it('reaches the group with the tab key on the selected tab only', () => {
      showTabs('closed-positions');

      expect(tab('Posizioni chiuse')).toHaveAttribute('tabindex', '0');
      expect(tab('Cicli')).toHaveAttribute('tabindex', '-1');
      expect(tab('Ordini')).toHaveAttribute('tabindex', '-1');
    });

    it('chooses the next and the previous tab with the arrows, round the ends', async () => {
      const chosen = showTabs('orders');
      tab('Ordini').focus();

      await userEvent.keyboard('{ArrowRight}');
      expect(tab('Cicli')).toHaveFocus();
      await userEvent.keyboard('{ArrowRight}');
      expect(tab('Posizioni chiuse')).toHaveFocus();
      await userEvent.keyboard('{ArrowLeft}');
      await userEvent.keyboard('{ArrowLeft}');

      expect(tab('Ordini')).toHaveFocus();
      expect(chosen).toEqual(['cycles', 'closed-positions', 'cycles', 'orders']);
    });

    it('chooses the first and the last tab with Home and End', async () => {
      const chosen = showTabs('closed-positions');
      tab('Posizioni chiuse').focus();

      await userEvent.keyboard('{End}');
      expect(tab('Ordini')).toHaveFocus();
      await userEvent.keyboard('{Home}');

      expect(tab('Cicli')).toHaveFocus();
      expect(chosen).toEqual(['orders', 'cycles']);
    });

    it('leaves the other keys to the page', async () => {
      const chosen = showTabs();
      tab('Cicli').focus();

      await userEvent.keyboard('{ArrowDown}a');

      expect(tab('Cicli')).toHaveFocus();
      expect(chosen).toEqual([]);
    });
  });
});
