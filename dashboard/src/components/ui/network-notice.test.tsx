import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import {
  isRealMoney,
  NetworkBadge,
  NetworkNotice,
  RealMoneyNotice,
  RealMoneyStartConfirmation,
  TestNetworkNotice,
} from './network-notice';

describe('network notice', () => {
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

  it('says the subject trades on the test network the API names, without real money', () => {
    render(<TestNetworkNotice subject="Il conto" networkName="sandbox" />);

    expect(screen.getByRole('note')).toHaveTextContent(
      'Il conto opererà sulla rete di test sandbox, senza denaro reale',
    );
  });

  it.each([
    ['real', 'Il conto opererà con denaro reale'],
    ['test', 'Il conto opererà sulla rete di test sandbox, senza denaro reale'],
  ])('warns of the network %s', (network, text) => {
    render(<NetworkNotice subject="Il conto" network={network} networkName="sandbox" />);

    expect(screen.getByRole('note')).toHaveTextContent(text);
  });

  it.each([
    ['real', 'REALE · sandbox'],
    ['test', 'TEST · sandbox'],
  ])('marks the network %s with the name the API gives it', (network, text) => {
    render(<NetworkBadge network={network} networkName="sandbox" />);

    expect(screen.getByText(text)).toBeInTheDocument();
  });
});
