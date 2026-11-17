import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { CommandButton, type CommandTone } from './command-button';
import {
  DESTRUCTIVE_COMMAND,
  GO_COMMAND,
  HOLD_COMMAND,
  PRIMARY_COMMAND,
  SECONDARY_COMMAND,
  STOP_COMMAND,
} from './commands';

describe('CommandButton', () => {
  it.each<[CommandTone, string]>([
    ['primary', PRIMARY_COMMAND],
    ['secondary', SECONDARY_COMMAND],
    ['destructive', DESTRUCTIVE_COMMAND],
    ['go', GO_COMMAND],
    ['hold', HOLD_COMMAND],
    ['stop', STOP_COMMAND],
  ])('shows the tone %s with its look', (tone, look) => {
    render(<CommandButton tone={tone}>Comando</CommandButton>);

    expect(screen.getByRole('button', { name: 'Comando' })).toHaveAttribute('class', look);
  });

  it('paints go green, hold amber and stop red', () => {
    expect(GO_COMMAND).toContain('bg-green-700');
    expect(HOLD_COMMAND).toContain('bg-amber-600');
    expect(STOP_COMMAND).toContain('bg-red-700');
  });

  it('writes the text of the pause in white, as the owner asked', () => {
    expect(HOLD_COMMAND).toContain('text-white');
    expect(HOLD_COMMAND).not.toContain('text-slate-950');
  });

  it('shows the icon next to the text, named by the text alone', () => {
    render(
      <CommandButton tone="hold" icon="pause">
        Pausa
      </CommandButton>,
    );

    const button = screen.getByRole('button', { name: 'Pausa' });
    expect(button).toHaveAccessibleName('Pausa');
    expect(button).toHaveTextContent(/^Pausa$/);
    const icon = within(button).getByRole('img', { hidden: true });
    expect(icon).toHaveAttribute('data-icon', 'pause');
    expect(icon).toHaveAttribute('aria-hidden', 'true');
  });

  it('shows no icon unless one is chosen', () => {
    render(<CommandButton tone="secondary">Duplica</CommandButton>);

    expect(
      within(screen.getByRole('button', { name: 'Duplica' })).queryByRole('img', { hidden: true }),
    ).toBeNull();
  });

  it('is a plain button unless it submits a form, and runs its command', async () => {
    const onClick = vi.fn();
    render(
      <>
        <CommandButton tone="go" onClick={onClick}>
          Avvia
        </CommandButton>
        <CommandButton tone="primary" type="submit">
          Salva
        </CommandButton>
      </>,
    );

    await userEvent.click(screen.getByRole('button', { name: 'Avvia' }));

    expect(onClick).toHaveBeenCalledOnce();
    expect(screen.getByRole('button', { name: 'Avvia' })).toHaveAttribute('type', 'button');
    expect(screen.getByRole('button', { name: 'Salva' })).toHaveAttribute('type', 'submit');
  });

  it('cannot be used while disabled', () => {
    render(
      <CommandButton tone="stop" disabled>
        Stop
      </CommandButton>,
    );

    expect(screen.getByRole('button', { name: 'Stop' })).toBeDisabled();
  });
});
