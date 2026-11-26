import { render, screen } from '@testing-library/react';
import { useForm } from 'react-hook-form';

import {
  DeclaredFields,
  declaredFieldOf,
  declaredInfoOf,
  type DeclaredField,
} from './declared-fields';

const FIELDS: readonly DeclaredField[] = [
  { name: 'account_address', label: 'Indirizzo del conto', secret: false },
  { name: 'secret_key', label: "Chiave dell'API wallet", secret: true },
];

type Values = { credentials: Record<string, string> };

const Form = ({ reasons = {} }: { readonly reasons?: Record<string, string> }) => {
  const { register } = useForm<Values>({ defaultValues: { credentials: {} } });
  return (
    <form>
      <DeclaredFields
        fields={FIELDS}
        infoOf={declaredInfoOf('che il conto chiede', "l'exchange")}
        registerField={(name) => register(`credentials.${name}`)}
        reasonOf={(name) => reasons[name]}
      />
    </form>
  );
};

describe('DeclaredFields', () => {
  it('asks each declared field by its label, in the order the API gives', () => {
    render(<Form />);

    expect(screen.getAllByRole('textbox').map((input) => input.getAttribute('name'))).toEqual([
      'credentials.account_address',
    ]);
    expect(screen.getByLabelText('Indirizzo del conto')).not.toHaveAttribute('type', 'password');
  });

  it('never shows a secret field in clear', () => {
    render(<Form />);

    expect(screen.getByLabelText("Chiave dell'API wallet")).toHaveAttribute('type', 'password');
    expect(screen.getByLabelText("Chiave dell'API wallet")).toHaveAttribute(
      'autocomplete',
      'new-password',
    );
  });

  it('keeps browser and password managers from filling any declared field (Bug 387)', () => {
    render(<Form />);

    for (const label of ['Indirizzo del conto', "Chiave dell'API wallet"]) {
      const input = screen.getByLabelText(label);
      expect(input).toHaveAttribute('data-lpignore', 'true');
      expect(input).toHaveAttribute('data-1p-ignore', 'true');
      expect(input).toHaveAttribute('data-bwignore', 'true');
    }
    expect(screen.getByLabelText('Indirizzo del conto')).toHaveAttribute('autocomplete', 'off');
  });

  it('shows the reason of a refusal beside its field', () => {
    render(<Form reasons={{ secret_key: "chiave dell'API wallet obbligatorio" }} />);

    expect(screen.getByText("chiave dell'API wallet obbligatorio")).toBeInTheDocument();
    expect(screen.getByLabelText("Chiave dell'API wallet")).toHaveAttribute('aria-invalid', 'true');
  });

  it('finds a field the API names only among those declared', () => {
    expect(declaredFieldOf(FIELDS, 'secret_key')?.label).toBe("Chiave dell'API wallet");
    expect(declaredFieldOf(FIELDS, 'memo')).toBeUndefined();
  });

  it('says of each declared field what it is for, who gives it and whether it is kept secret (R5.5.7)', () => {
    const infoOf = declaredInfoOf('che il conto chiede', "l'exchange");

    expect(FIELDS.map(infoOf)).toEqual([
      "Indirizzo del conto: dato che il conto chiede, conservato in chiaro. Il valore che ti dà l'exchange. Obbligatorio.",
      "Chiave dell'API wallet: dato segreto che il conto chiede, conservato cifrato e mai più mostrato. Il valore che ti dà l'exchange. Obbligatorio.",
    ]);
  });
});
