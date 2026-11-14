import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { SessionExpiredError } from '@/lib/auth';

import { ConfirmationDialog } from './confirmation-dialog';

const renderDialog = (props: Partial<Parameters<typeof ConfirmationDialog>[0]> = {}) => {
  const onConfirm = vi.fn();
  const onCancel = vi.fn();
  render(
    <ConfirmationDialog
      confirmLabel="Conferma la rimozione"
      title="Rimozione del conto principale"
      onConfirm={onConfirm}
      onCancel={onCancel}
      pending={false}
      {...props}
    >
      Il conto principale sarà rimosso.
    </ConfirmationDialog>,
  );
  return { onConfirm, onCancel };
};

describe('ConfirmationDialog', () => {
  it('names what it asks to confirm and says what will happen', () => {
    renderDialog();

    const dialog = screen.getByRole('alertdialog', { name: 'Rimozione del conto principale' });
    expect(dialog).toHaveAccessibleDescription('Il conto principale sarà rimosso.');
  });

  it('confirms or cancels at the choice of the user', async () => {
    const { onConfirm, onCancel } = renderDialog();

    await userEvent.click(screen.getByRole('button', { name: 'Conferma la rimozione' }));
    await userEvent.click(screen.getByRole('button', { name: 'Annulla' }));

    expect(onConfirm).toHaveBeenCalledOnce();
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it('does not confirm twice while the operation runs', () => {
    renderDialog({ pending: true });

    expect(screen.getByRole('button', { name: 'Conferma la rimozione' })).toBeDisabled();
  });

  it('tells why the operation failed', () => {
    renderDialog({ error: new Error('chiave usata da flussi attivi o in pausa: alfa') });

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Operazione non riuscita: chiave usata da flussi attivi o in pausa: alfa',
    );
  });

  it('says nothing about an expired session', () => {
    renderDialog({ error: new SessionExpiredError() });

    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
