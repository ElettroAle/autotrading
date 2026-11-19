import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import type { KeyExpiry } from '@/types/key-expiry';

import { ExpiringKeysNotice, ExpiryDateForm, KeyExpiryStatus } from './key-expiry';

const DAY = '2026-12-15';

const expiryOf = (change: Partial<KeyExpiry>): KeyExpiry => ({
  expiry: { expires_on: DAY, source: 'entered' },
  expiry_status: 'valid',
  days_left: 40,
  expiry_editable: true,
  ...change,
});

const UNKNOWN = expiryOf({ expiry: null, expiry_status: 'unknown', days_left: null });

describe('KeyExpiryStatus', () => {
  it.each([
    [UNKNOWN, 'scadenza sconosciuta', null],
    [expiryOf({}), 'scade il 15/12/2026', null],
    [
      expiryOf({ expiry_status: 'expiring', days_left: 7 }),
      'scade tra 7 giorni · 15/12/2026',
      'triangle-alert',
    ],
    [
      expiryOf({ expiry_status: 'expiring', days_left: 1 }),
      'scade domani · 15/12/2026',
      'triangle-alert',
    ],
    [expiryOf({ expiry_status: 'expired', days_left: 0 }), 'scaduta · 15/12/2026', 'circle-alert'],
  ])('tells the state the API reads, with its icon beside the text', (expiry, text, icon) => {
    render(<KeyExpiryStatus expiry={expiry} readBy="dal fornitore" />);

    const status = screen.getByLabelText('Scadenza della chiave');
    expect(status).toHaveTextContent(text);
    const drawn = within(status).queryByRole('img', { hidden: true });
    expect(drawn?.getAttribute('data-icon') ?? null).toBe(icon);
  });

  it('says a date read by the adapter is read', () => {
    render(
      <KeyExpiryStatus
        expiry={expiryOf({ expiry: { expires_on: DAY, source: 'read' }, expiry_editable: false })}
        readBy="dall'exchange"
      />,
    );

    expect(screen.getByLabelText('Scadenza della chiave')).toHaveTextContent(
      "scade il 15/12/2026 · letta dall'exchange",
    );
  });
});

describe('ExpiringKeysNotice', () => {
  it('stays silent while no key expires within 30 days', () => {
    const { container } = render(
      <ExpiringKeysNotice keys={[{ name: 'openrouter', expiry: UNKNOWN, renewal: null }]} />,
    );

    expect(container).toBeEmptyDOMElement();
  });

  it('tells every key that expires or expired, with the command to renew it', () => {
    render(
      <ExpiringKeysNotice
        keys={[
          {
            name: 'openrouter',
            expiry: expiryOf({ expiry_status: 'expiring', days_left: 7 }),
            renewal: <button type="button">Sostituisci la chiave di openrouter</button>,
          },
          { name: 'anthropic', expiry: expiryOf({}), renewal: null },
          {
            name: 'openai',
            expiry: expiryOf({ expiry_status: 'expired', days_left: -2 }),
            renewal: <button type="button">Sostituisci la chiave di openai</button>,
          },
        ]}
      />,
    );

    const notice = screen.getByRole('region', { name: 'Chiavi da rinnovare' });
    expect(notice).toHaveTextContent('Chiave openrouter: scade tra 7 giorni');
    expect(notice).toHaveTextContent('Chiave openai: scaduta');
    expect(notice).not.toHaveTextContent('anthropic');
    expect(screen.getByRole('button', { name: 'Sostituisci la chiave di openai' })).toBeVisible();
  });
});

describe('ExpiryDateForm', () => {
  it('saves the day entered, and no day forgets the date', async () => {
    const onSave = vi.fn();
    const onCancel = vi.fn();
    render(
      <ExpiryDateForm
        subject="openrouter"
        current={DAY}
        pending={false}
        error={null}
        onSave={onSave}
        onCancel={onCancel}
      />,
    );
    const field = screen.getByLabelText('Scadenza');
    expect(field).toHaveValue(DAY);

    await userEvent.clear(field);
    await userEvent.type(field, '2027-03-15');
    await userEvent.click(screen.getByRole('button', { name: 'Salva la scadenza' }));
    await userEvent.clear(field);
    await userEvent.click(screen.getByRole('button', { name: 'Salva la scadenza' }));
    await userEvent.click(screen.getByRole('button', { name: 'Annulla' }));

    expect(onSave.mock.calls).toEqual([['2027-03-15'], [null]]);
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it('tells why the date was refused', () => {
    render(
      <ExpiryDateForm
        subject="openrouter"
        current={undefined}
        pending
        error={new Error("la scadenza di queste credenziali la legge l'exchange")}
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByRole('form', { name: 'Scadenza di openrouter' })).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent(
      "Impossibile salvare la scadenza: la scadenza di queste credenziali la legge l'exchange",
    );
    expect(screen.getByRole('button', { name: 'Salva la scadenza' })).toBeDisabled();
  });
});
