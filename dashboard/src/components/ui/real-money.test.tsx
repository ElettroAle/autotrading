import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { isRealMoney, RealMoneyNotice, RealMoneyStartConfirmation } from './real-money';

describe('real money', () => {
  it('is only the real network', () => {
    expect(isRealMoney('real')).toBe(true);
    expect(isRealMoney('test')).toBe(false);
    expect(isRealMoney(undefined)).toBe(false);
  });

  it('says that the subject will trade real money', () => {
    render(<RealMoneyNotice subject="Il conto" />);

    expect(screen.getByRole('note')).toHaveTextContent('Il conto opererà con denaro reale');
  });

  it('asks to confirm a start on real money', async () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(
      <RealMoneyStartConfirmation onConfirm={onConfirm} onCancel={onCancel} pending={false} />,
    );

    const dialog = screen.getByRole('alertdialog', { name: "Conferma dell'avvio" });
    expect(dialog).toHaveTextContent('Il flusso opererà con denaro reale');
    await userEvent.click(screen.getByRole('button', { name: 'Avvia con denaro reale' }));
    await userEvent.click(screen.getByRole('button', { name: 'Annulla' }));

    expect(onConfirm).toHaveBeenCalledOnce();
    expect(onCancel).toHaveBeenCalledOnce();
  });
});
