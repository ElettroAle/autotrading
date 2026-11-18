import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { ActionsMenu } from './actions-menu';

const LABEL = 'Azioni del conto principale';

const renderMenu = () => {
  const replace = vi.fn();
  const remove = vi.fn();
  render(
    <>
      <ActionsMenu
        label={LABEL}
        actions={[
          { name: 'Sostituisci le credenziali', onSelect: replace },
          { name: 'Rimuovi', onSelect: remove, destructive: true },
        ]}
      />
      <p>fuori dal menu</p>
    </>,
  );
  return { replace, remove };
};

const trigger = () => screen.getByRole('button', { name: LABEL });

const menu = () => screen.queryByRole('menu', { name: LABEL });

// ADR elenco-dei-conti-e-pagina-del-conto: the actions of an element of a list stay in a menu «Azioni».
describe('ActionsMenu', () => {
  it('shows «Azioni», named by its label, with the menu closed', () => {
    renderMenu();

    expect(trigger()).toHaveTextContent('Azioni');
    expect(trigger()).toHaveAttribute('aria-haspopup', 'menu');
    expect(trigger()).toHaveAttribute('aria-expanded', 'false');
    expect(menu()).not.toBeInTheDocument();
  });

  it('opens the actions, the first one focused', async () => {
    renderMenu();

    await userEvent.click(trigger());

    expect(trigger()).toHaveAttribute('aria-expanded', 'true');
    const items = within(menu() ?? document.body).getAllByRole('menuitem');
    expect(items.map((item) => item.textContent)).toEqual([
      'Sostituisci le credenziali',
      'Rimuovi',
    ]);
    expect(items[0]).toHaveFocus();
    expect(items[1]).toHaveClass('text-red-800');
  });

  it('runs the action chosen and closes', async () => {
    const { replace, remove } = renderMenu();

    await userEvent.click(trigger());
    await userEvent.click(screen.getByRole('menuitem', { name: 'Rimuovi' }));

    expect(remove).toHaveBeenCalledOnce();
    expect(replace).not.toHaveBeenCalled();
    expect(menu()).not.toBeInTheDocument();
  });

  it('moves among the actions with the arrows, round the ends', async () => {
    renderMenu();
    await userEvent.click(trigger());
    const [first, second] = screen.getAllByRole('menuitem');

    await userEvent.keyboard('{ArrowDown}');
    expect(second).toHaveFocus();
    await userEvent.keyboard('{ArrowDown}');
    expect(first).toHaveFocus();
    await userEvent.keyboard('{ArrowUp}');
    expect(second).toHaveFocus();
    await userEvent.keyboard('{a}');
    expect(second).toHaveFocus();
  });

  it('closes with Esc, giving the focus back to «Azioni»', async () => {
    renderMenu();
    await userEvent.click(trigger());

    await userEvent.keyboard('{Escape}');

    expect(menu()).not.toBeInTheDocument();
    expect(trigger()).toHaveFocus();
  });

  it('ignores Esc while closed', async () => {
    renderMenu();
    trigger().focus();

    await userEvent.keyboard('{Escape}');

    expect(menu()).not.toBeInTheDocument();
    expect(trigger()).toHaveFocus();
  });

  it('closes with a click outside, and not with a click inside', async () => {
    renderMenu();
    await userEvent.click(trigger());

    await userEvent.click(screen.getByRole('menu', { name: LABEL }));
    expect(menu()).toBeInTheDocument();
    await userEvent.click(screen.getByText('fuori dal menu'));

    expect(menu()).not.toBeInTheDocument();
  });

  it('closes when «Azioni» is touched again', async () => {
    renderMenu();
    await userEvent.click(trigger());

    await userEvent.click(trigger());

    expect(menu()).not.toBeInTheDocument();
  });
});
