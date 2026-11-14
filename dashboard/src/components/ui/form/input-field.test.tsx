import { render, screen } from '@testing-library/react';

import { FormAlert, InputField, SecretField } from './input-field';

describe('InputField', () => {
  it('labels its input and has no reason when the value is accepted', () => {
    render(<InputField label="Nome" name="name" defaultValue="principale" />);

    const input = screen.getByLabelText('Nome');
    expect(input).toHaveValue('principale');
    expect(input).not.toHaveAttribute('aria-invalid');
    expect(input).not.toHaveAccessibleDescription();
  });

  it('shows the reason beside the field it concerns', () => {
    render(<InputField label="Nome" name="name" error={{ message: 'nome obbligatorio' }} />);

    const input = screen.getByLabelText('Nome');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(input).toHaveAccessibleDescription('nome obbligatorio');
  });
});

describe('SecretField', () => {
  it('hides what is typed and asks the browser not to remember it (ADR 0130)', () => {
    render(<SecretField label="Chiave" name="key" />);

    const input = screen.getByLabelText('Chiave');
    expect(input).toHaveAttribute('type', 'password');
    expect(input).toHaveAttribute('autocomplete', 'off');
  });
});

describe('FormAlert', () => {
  it('tells the reason at the head of the form', () => {
    render(<FormAlert error={{ message: 'nome del conto già in uso' }} />);

    expect(screen.getByRole('alert')).toHaveTextContent('nome del conto già in uso');
  });

  it('says nothing without a reason', () => {
    render(<FormAlert error={undefined} />);

    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
