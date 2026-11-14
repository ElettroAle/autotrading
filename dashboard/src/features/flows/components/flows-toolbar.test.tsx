import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { fakePlatform } from '@/testing/mocks/platform';
import { renderInApp } from '@/testing/test-utils';

import { FlowsToolbar } from './flows-toolbar';

// Once open, the form has its own «Importa» that sends the file: the command is the one that opens and closes it.
const importCommand = (expanded: boolean) =>
  screen.getByRole('button', { name: 'Importa', expanded });

describe('FlowsToolbar', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
  });

  it('offers a new flow and the import of a strategy', async () => {
    await renderInApp(<FlowsToolbar />, { account: 'anna' });

    expect(await screen.findByRole('link', { name: 'Nuovo flusso' })).toHaveAttribute(
      'href',
      '/flows/new',
    );
    expect(importCommand(false)).toBeVisible();
  });

  it('keeps the import closed until the user asks for it', async () => {
    await renderInApp(<FlowsToolbar />, { account: 'anna' });

    await screen.findByRole('link', { name: 'Nuovo flusso' });

    expect(screen.queryByRole('form', { name: 'Importazione di una strategia' })).toBeNull();
  });

  it('opens and closes the import of a strategy on request', async () => {
    await renderInApp(<FlowsToolbar />, { account: 'anna' });

    await userEvent.click(await screen.findByRole('button', { name: 'Importa' }));

    const form = screen.getByRole('form', { name: 'Importazione di una strategia' });
    expect(form).toBeVisible();
    expect(importCommand(true)).toHaveAttribute('aria-controls');

    await userEvent.click(importCommand(true));

    expect(screen.queryByRole('form', { name: 'Importazione di una strategia' })).toBeNull();
    expect(importCommand(false)).toBeVisible();
  });
});
