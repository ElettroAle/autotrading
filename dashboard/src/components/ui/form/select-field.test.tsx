import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { SessionExpiredError } from '@/lib/auth';

import { SelectField, type SelectChoice } from './select-field';

const EXCHANGES: SelectChoice[] = [
  { value: 'hyperliquid', label: 'hyperliquid' },
  { value: 'okx', label: 'okx' },
];

const optionNames = () => screen.getAllByRole('option').map((option) => option.textContent);

describe('SelectField', () => {
  it('offers the choices of the list after a placeholder that leaves the field empty', () => {
    render(<SelectField label="Exchange" placeholder="Scegli un exchange" choices={EXCHANGES} />);

    const field = screen.getByRole('combobox', { name: 'Exchange' });
    expect(optionNames()).toEqual(['Scegli un exchange', 'hyperliquid', 'okx']);
    expect(field).toHaveValue('');
    expect(field).toBeEnabled();
  });

  it('takes no value outside the list', () => {
    render(<SelectField label="Exchange" placeholder="Scegli un exchange" choices={EXCHANGES} />);
    const field = screen.getByRole<HTMLSelectElement>('combobox', { name: 'Exchange' });

    field.value = 'binance';

    expect(field.value).toBe('');
  });

  it('lets the user choose an option of the list', async () => {
    const chosen = vi.fn();
    render(
      <SelectField
        label="Exchange"
        placeholder="Scegli un exchange"
        choices={EXCHANGES}
        onChange={(event) => chosen(event.target.value)}
      />,
    );

    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Exchange' }), 'okx');

    expect(chosen).toHaveBeenCalledWith('okx');
  });

  it('shows an option that cannot be chosen with its note', () => {
    render(
      <SelectField
        label="Fornitore"
        placeholder="Scegli un fornitore"
        choices={[
          {
            value: 'openrouter',
            label: 'openrouter',
            disabled: true,
            note: 'chiave già registrata',
          },
          { value: 'anthropic', label: 'anthropic' },
        ]}
      />,
    );

    expect(
      screen.getByRole('option', { name: 'openrouter · chiave già registrata' }),
    ).toBeDisabled();
    expect(screen.getByRole('option', { name: 'anthropic' })).toBeEnabled();
  });

  it('groups the options under the label of their group', () => {
    render(
      <SelectField
        label="Modello"
        placeholder="Scegli un modello"
        choices={[
          {
            label: 'openai · chiave mancante',
            options: [{ value: 'openai/gpt-4o', label: 'openai/gpt-4o', disabled: true }],
          },
        ]}
      />,
    );

    const group = screen.getByRole('group', { name: 'openai · chiave mancante' });
    expect(within(group).getByRole('option', { name: 'openai/gpt-4o' })).toBeDisabled();
  });

  it('cannot be used while the list is read', () => {
    render(<SelectField label="Exchange" placeholder="Scegli un exchange" choices={[]} loading />);

    expect(screen.getByRole('combobox', { name: 'Exchange' })).toBeDisabled();
    expect(optionNames()).toEqual(['Caricamento…']);
  });

  it('says why the list is not available and cannot be used', () => {
    render(
      <SelectField
        label="Exchange"
        placeholder="Scegli un exchange"
        choices={[]}
        unavailable={{
          prefix: 'Impossibile leggere gli exchange',
          error: new Error('errore interno'),
        }}
      />,
    );

    expect(screen.getByRole('combobox', { name: 'Exchange' })).toBeDisabled();
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Impossibile leggere gli exchange: errore interno',
    );
  });

  it('says nothing more of a list lost to an expired session, and still cannot be used', () => {
    render(
      <SelectField
        label="Exchange"
        placeholder="Scegli un exchange"
        choices={[]}
        unavailable={{
          prefix: 'Impossibile leggere gli exchange',
          error: new SessionExpiredError(),
        }}
      />,
    );

    expect(screen.getByRole('combobox', { name: 'Exchange' })).toBeDisabled();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('shows the reason a value was refused beside the field', () => {
    render(
      <SelectField
        label="Exchange"
        placeholder="Scegli un exchange"
        choices={EXCHANGES}
        error={{ message: 'Campo obbligatorio' }}
      />,
    );

    const field = screen.getByRole('combobox', { name: 'Exchange' });
    expect(field).toHaveAttribute('aria-invalid', 'true');
    expect(field).toHaveAccessibleDescription('Campo obbligatorio');
  });

  it('keeps the identifier it is given, so a label elsewhere can name it', () => {
    render(
      <SelectField id="flow-model" label="Modello" placeholder="Scegli un modello" choices={[]} />,
    );

    expect(screen.getByRole('combobox', { name: 'Modello' })).toHaveAttribute('id', 'flow-model');
  });
});
